
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "jobbridge-local-dev-key-change-this")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "job_bridge_db")

    # Enable SSL for Aiven when a CA certificate is available
    MYSQL_CUSTOM_OPTIONS = {}

    if os.getenv("MYSQL_HOST", "").endswith("aivencloud.com"):
        MYSQL_CUSTOM_OPTIONS = {
            "ssl": {
                "ca": os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "ca.pem"
                )
            }
        }
