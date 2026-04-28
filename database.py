from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ==================== USUARIOS ====================
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id       = db.Column(db.Integer, primary_key=True)
    nombre   = db.Column(db.String(100), nullable=False)
    usuario  = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol      = db.Column(db.String(20), default='vendedor')
    activo   = db.Column(db.Boolean, default=True)

# ==================== PRODUCTOS ====================
class Producto(db.Model):
    __tablename__ = 'productos'
    id              = db.Column(db.Integer, primary_key=True)
    nombre          = db.Column(db.String(100), nullable=False)
    categoria       = db.Column(db.String(50),  nullable=False)
    unidad_medida   = db.Column(db.String(20),  nullable=False)
    cantidad_medida = db.Column(db.Float,        nullable=False)
    variedad        = db.Column(db.String(100),  default='General')
    precio_venta    = db.Column(db.Float,        nullable=False)
    stock           = db.Column(db.Float,        default=0)
    descripcion     = db.Column(db.Text,         default='')
    fecha_registro  = db.Column(db.String(20),
                        default=datetime.now().strftime("%Y-%m-%d"))
    activo          = db.Column(db.Boolean,      default=True)

# ==================== CLIENTES ====================
class Cliente(db.Model):
    __tablename__ = 'clientes'
    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    telefono       = db.Column(db.String(20),  default='')
    direccion      = db.Column(db.String(200), default='')
    email          = db.Column(db.String(100), default='')
    fecha_registro = db.Column(db.String(20),
                        default=datetime.now().strftime("%Y-%m-%d"))
    activo         = db.Column(db.Boolean, default=True)

# ==================== VENTAS ====================
class Venta(db.Model):
    __tablename__ = 'ventas'
    id             = db.Column(db.Integer, primary_key=True)
    fecha          = db.Column(db.String(20), nullable=False)
    hora           = db.Column(db.String(10), nullable=False)
    cliente_nombre = db.Column(db.String(100), default='Público General')
    usuario_id     = db.Column(db.Integer,
                        db.ForeignKey('usuarios.id'))
    total          = db.Column(db.Float,   nullable=False)
    observaciones  = db.Column(db.Text,    default='')
    anulada        = db.Column(db.Boolean, default=False)
    detalles       = db.relationship('DetalleVenta',
                        backref='venta', lazy=True)

# ==================== DETALLE VENTAS ====================
class DetalleVenta(db.Model):
    __tablename__   = 'detalle_ventas'
    id              = db.Column(db.Integer, primary_key=True)
    venta_id        = db.Column(db.Integer,
                        db.ForeignKey('ventas.id'))
    producto_id     = db.Column(db.Integer,
                        db.ForeignKey('productos.id'))
    cantidad        = db.Column(db.Float, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal        = db.Column(db.Float, nullable=False)
    producto        = db.relationship('Producto')

# ==================== INSUMOS ====================
class Insumo(db.Model):
    __tablename__  = 'insumos'
    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    unidad_medida  = db.Column(db.String(20),  nullable=False)
    stock          = db.Column(db.Float,  default=0)
    stock_minimo   = db.Column(db.Float,  default=5)
    activo         = db.Column(db.Boolean, default=True)

# ==================== COMPRAS ====================
class Compra(db.Model):
    __tablename__   = 'compras'
    id              = db.Column(db.Integer, primary_key=True)
    fecha           = db.Column(db.String(20), nullable=False)
    hora            = db.Column(db.String(10), nullable=False)
    insumo_id       = db.Column(db.Integer,
                        db.ForeignKey('insumos.id'))
    cantidad        = db.Column(db.Float, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    precio_total    = db.Column(db.Float, nullable=False)
    proveedor       = db.Column(db.String(100),
                        default='No especificado')
    observaciones   = db.Column(db.Text, default='')
    insumo          = db.relationship('Insumo')
