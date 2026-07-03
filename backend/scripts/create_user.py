"""
Kullanıcı oluşturma CLI (Command Line Interface) betiği.

Bu betik, veritabanına yeni bir kullanıcı (admin, operator, viewer) eklemek için kullanılır.
Parametreler komut satırından verilebilir veya interaktif olarak sorulur.
"""
import sys
import argparse
import bcrypt
from sqlalchemy.orm import Session

# backend/ klasörünü Python arama yoluna (sys.path) ekle
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.infrastructure.database.database import SessionLocal, Base, engine
from src.infrastructure.database.models import UserModel
from src.domain.entities.user import UserRole


def create_user(username: str, password_plain: str, role_str: str) -> None:
    """Veritabanında yeni bir kullanıcı oluşturur ve kaydeder.

    Args:
        username: Kullanıcı adı.
        password_plain: Düz metin şifre.
        role_str: Kullanıcı rolü (admin, operator, viewer).
    """
    try:
        role = UserRole(role_str.lower())
    except ValueError:
        print(f"❌ Hata: Geçersiz rol '{role_str}'. Geçerli roller: {[r.value for r in UserRole]}")
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        # Önce veritabanının ve tabloların hazır olduğundan emin olalım
        Base.metadata.create_all(bind=engine)

        # Kullanıcı adı kontrolü
        existing = db.query(UserModel).filter(UserModel.username == username).first()
        if existing:
            print(f"❌ Hata: '{username}' kullanıcı adı zaten mevcut!")
            sys.exit(1)

        # Şifreyi bcrypt ile hash'leme (şifreleme)
        password_hash = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        new_user = UserModel(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"✅ Kullanıcı başarıyla oluşturuldu:")
        print(f"   Kullanıcı Adı: {username}")
        print(f"   Rol          : {role.value}")
    except Exception as e:
        db.rollback()
        print(f"❌ Veritabanı işlemi sırasında hata oluştu: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


def main():
    """Betiğin ana giriş noktası."""
    parser = argparse.ArgumentParser(description="Veritabanında yeni bir kullanıcı oluşturur.")
    parser.add_argument("-u", "--username", help="Kullanıcı adı")
    parser.add_argument("-p", "--password", help="Düz metin şifre")
    parser.add_argument("-r", "--role", help="Kullanıcı rolü (admin, operator, viewer)", default="admin")

    args = parser.parse_args()

    # Eğer argümanlar verilmemişse interaktif modda soralım
    username = args.username
    password = args.password
    role = args.role

    if not username:
        username = input("Kullanıcı adı girin: ").strip()
        if not username:
            print("❌ Hata: Kullanıcı adı boş olamaz!")
            sys.exit(1)

    if not password:
        import getpass
        password = getpass.getpass("Şifre girin: ").strip()
        if not password:
            print("❌ Hata: Şifre boş olamaz!")
            sys.exit(1)

    create_user(username, password, role)


if __name__ == "__main__":
    main()
