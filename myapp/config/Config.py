# myapp/Config.py

class Config:
    # Configuración para la conexión a la base de datos MySQL.
    # JDBC: jdbc:mysql://localhost:3306/db_sys_expert
    # Cadena convertida a SQLAlchemy:
    # SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:1q2w3e4r5t6y@localhost:3306/db_sys_expert'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:YkczPlBVMrrmzynWQDeTRvGiyRfWbuxq@yamanote.proxy.rlwy.net:17807/db_sys_expert'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

