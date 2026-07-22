import os
import cv2
import numpy as np
from typing import Sequence, Tuple
import onnxruntime as ort

from src.domain.entities.alarm import BoundingBox
from src.domain.interfaces.ai_inference_service import IAIInferenceService, Detection

# backend/models/ klasörüne mutlak yol — CWD'den bağımsız
_DEFAULT_MODEL_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "models", "yolov8n.onnx")
)

class ONNXInferenceService(IAIInferenceService):
    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH, conf_threshold: float = 0.5, iou_threshold: float = 0.45):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # GPU (DirectML) varsa kullanır, yoksa otomatik CPU'ya düşer.
        # DirectML, Windows üzerindeki tüm GPU'ları (Nvidia, AMD, Intel) DirectX 12 üzerinden kullanır.
        import warnings
        available = ort.get_available_providers()
        providers = [p for p in ['DmlExecutionProvider', 'CPUExecutionProvider'] if p in available]
        if not providers:
            providers = ['CPUExecutionProvider']

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.session = ort.InferenceSession(self.model_path, providers=providers)
            self._input_name = self.session.get_inputs()[0].name
            self._output_name = self.session.get_outputs()[0].name
            self._input_shape = self.session.get_inputs()[0].shape
            active = self.session.get_providers()[0]
            print(f"[AI] ONNX modeli yüklendi — provider: {active}")
        except Exception as e:
            self.session = None
            print(f"[AI] ONNX modeli yüklenemedi: {e}")

    def _letterbox(self, img: np.ndarray, new_shape=(640, 640), color=(114, 114, 114)) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        # En-boy oranı (Aspect ratio) korunarak görüntüyü yeniden boyutlandırma işlemi (Letterbox)
        shape = img.shape[:2]  # Mevcut boyutlar [yükseklik, genişlik] (current shape [height, width])
        
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # Genişlik ve yükseklik boşlukları (wh padding)
        dw /= 2  # Boşluğu iki kenara böl (divide padding into 2 sides)
        dh /= 2
        
        if shape[::-1] != new_unpad:  # Yeniden boyutlandır (resize)
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        return img, r, (dw, dh)

    def _preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        input_width, input_height = self._input_shape[3], self._input_shape[2]
        if isinstance(input_width, str): 
            # Dinamik boyutları idare et (Handle dynamic shapes if any)
            input_width, input_height = 640, 640
            
        img, ratio, (dw, dh) = self._letterbox(frame, new_shape=(input_width, input_height))
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # HWC (Yükseklik, Genişlik, Kanal) formatından CHW (Kanal, Yükseklik, Genişlik) formatına çevir (HWC to CHW format)
        img = img.transpose((2, 0, 1))
        # Normalize et (0-1 aralığına çek) (Normalize)
        img = img.astype(np.float32) / 255.0
        # Batch (Yığın) boyutu ekle (Expand dims)
        img = np.expand_dims(img, axis=0)
        return img, ratio, (dw, dh)

    def detect_humans(
        self,
        frame: object,
        conf_threshold: float | None = None,
        iou_threshold: float | None = None,
    ) -> Sequence[Detection]:
        if not self.session or frame is None:
            return []
        active_conf_threshold = conf_threshold if conf_threshold is not None else self.conf_threshold
        active_iou_threshold = iou_threshold if iou_threshold is not None else self.iou_threshold

        orig_h, orig_w = frame.shape[:2]
        img, ratio, (dw, dh) = self._preprocess(frame)

        # Çıkarım işlemini gerçekleştir (Inference)
        outputs = self.session.run([self._output_name], {self._input_name: img})
        output = outputs[0][0]
        
        # Çıktı boyutunu (Output shape) çözümle ([84, 8400] veya [8400, 84])
        if output.shape[0] < output.shape[1]:
            output = output.T # Şimdi (Now) [8400, 84] formatında
            
        # Çıktı formatı artık [8400, 84] (output shape is [8400, 84])
        boxes = output[:, :4]
        scores = output[:, 4:]
        
        person_scores = scores[:, 0]
        
        valid_indices = np.where(person_scores > active_conf_threshold)[0]
        
        if len(valid_indices) == 0:
            return []
            
        filtered_boxes = boxes[valid_indices]
        filtered_scores = person_scores[valid_indices]
        
        # NMS (Maksimum Olmayanları Bastırma - Non-Maximum Suppression) Uygula
        # NMS için xywh (merkez x, merkez y, genişlik, yükseklik) formatını xyxy (sol üst x, sol üst y) formatına çevir
        x_centers = filtered_boxes[:, 0]
        y_centers = filtered_boxes[:, 1]
        widths = filtered_boxes[:, 2]
        heights = filtered_boxes[:, 3]
        
        x1 = x_centers - widths / 2
        y1 = y_centers - heights / 2
        
        # cv2.dnn.NMSBoxes xyxy yerine [x, y, w, h] formatı alır. 
        # Ancak buradaki x ve y merkez koordinatları değil, sol üst (top-left) köşeyi temsil etmelidir.
        bboxes_for_nms = np.stack((x1, y1, widths, heights), axis=1).tolist()
        
        indices = cv2.dnn.NMSBoxes(bboxes_for_nms, filtered_scores.tolist(), active_conf_threshold, active_iou_threshold)
        
        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                score = float(filtered_scores[i])
                
                # Orijinal x_center (merkez x), y_center (merkez y), w (genişlik), h (yükseklik) değerlerini geri al
                xc, yc, w, h = filtered_boxes[i]
                
                # Letterbox (yeniden boyutlandırma) işlemini tersine çevir (Reverse letterbox)
                xc = (xc - dw) / ratio
                yc = (yc - dh) / ratio
                w = w / ratio
                h = h / ratio
                
                x_topleft = int(xc - w / 2)
                y_topleft = int(yc - h / 2)
                box_w = int(w)
                box_h = int(h)
                
                # Koordinatların görüntü sınırları dışına taşmasını engelle (Clip coordinates properly)
                x = max(0, x_topleft)
                y = max(0, y_topleft)
                x2 = min(orig_w, x_topleft + box_w)
                y2 = min(orig_h, y_topleft + box_h)
                
                final_w = max(0, x2 - x)
                final_h = max(0, y2 - y)
                
                if final_w > 0 and final_h > 0:
                    bbox = BoundingBox(x=x, y=y, width=final_w, height=final_h)
                    detections.append(Detection(label="person", confidence=score, bounding_box=bbox))
                
        return detections
