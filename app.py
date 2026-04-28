from flask import (Flask, render_template, request,
                   redirect, url_for, session,
                   jsonify, flash)
from database import (db, Usuario, Producto, Cliente,
                      Venta, DetalleVenta, Insumo, Compra)
from datetime import datetime, timedelta
from werkzeug.security import (generate_password_hash,
                                check_password_hash)
from functools import wraps
import os

# ══════════════════════════════════════════════
#              CONFIGURACIÓN
# ══════════════════════════════════════════════
app = Flask(__name__)
app.secret_key = os.environ.get(
    'SECRET_KEY', 'sumak_clave_2024')

DATABASE_URL = os.environ.get(
    'DATABASE_URL', 'sqlite:///sumak.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace(
        'postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI']        = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Crear tablas y admin inicial
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(usuario='admin').first():
        admin = Usuario(
            nombre='Administrador',
            usuario='admin',
            password=generate_password_hash('admin123'),
            rol='admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado: admin / admin123")

# ══════════════════════════════════════════════
#              DECORADOR LOGIN
# ══════════════════════════════════════════════
def login_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorador

# Pasar fecha a todas las plantillas
@app.context_processor
def variables_globales():
    return {'now': datetime.now().strftime("%d/%m/%Y %H:%M")}

# ══════════════════════════════════════════════
#              LOGIN / LOGOUT
# ══════════════════════════════════════════════
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        usu = request.form.get('usuario', '').strip()
        pwd = request.form.get('password', '').strip()
        usuario = Usuario.query.filter_by(
            usuario=usu, activo=True).first()

        if usuario and check_password_hash(
                usuario.password, pwd):
            session['usuario_id']     = usuario.id
            session['usuario_nombre'] = usuario.nombre
            session['usuario_rol']    = usuario.rol
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Usuario o contraseña incorrectos',
                  'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ══════════════════════════════════════════════
#              DASHBOARD
# ══════════════════════════════════════════════
@app.route('/dashboard')
@login_requerido
def dashboard():
    hoy = datetime.now().strftime("%Y-%m-%d")

    ventas_hoy   = Venta.query.filter_by(
        fecha=hoy, anulada=False).all()
    total_hoy    = sum(v.total for v in ventas_hoy)
    total_prods  = Producto.query.filter_by(activo=True).count()
    total_clts   = Cliente.query.filter_by(activo=True).count()
    compras_hoy  = Compra.query.filter_by(fecha=hoy).all()
    total_comp   = sum(c.precio_total for c in compras_hoy)

    # Ventas últimos 7 días para gráfica
    fechas  = []
    totales = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i))
        vds = Venta.query.filter_by(
            fecha=d.strftime("%Y-%m-%d"),
            anulada=False).all()
        fechas.append(d.strftime("%d/%m"))
        totales.append(sum(v.total for v in vds))

    ultimas = Venta.query.filter_by(
        anulada=False).order_by(
        Venta.id.desc()).limit(5).all()

    alertas = Insumo.query.filter(
        Insumo.stock <= Insumo.stock_minimo,
        Insumo.activo == True).all()

    return render_template('dashboard.html',
        total_hoy       = total_hoy,
        num_ventas_hoy  = len(ventas_hoy),
        total_productos = total_prods,
        total_clientes  = total_clts,
        total_compras   = total_comp,
        fechas          = fechas,
        totales         = totales,
        ultimas_ventas  = ultimas,
        alertas         = alertas)

# ══════════════════════════════════════════════
#              PRODUCTOS
# ══════════════════════════════════════════════
@app.route('/productos')
@login_requerido
def productos():
    buscar = request.args.get('buscar', '')
    if buscar:
        lista = Producto.query.filter(
            Producto.activo == True,
            db.or_(
                Producto.nombre.ilike(f'%{buscar}%'),
                Producto.variedad.ilike(f'%{buscar}%'),
                Producto.categoria.ilike(f'%{buscar}%')
            )).order_by(Producto.nombre).all()
    else:
        lista = Producto.query.filter_by(
            activo=True).order_by(Producto.nombre).all()
    return render_template('productos.html',
                           productos=lista,
                           buscar=buscar)

@app.route('/productos/nuevo', methods=['GET', 'POST'])
@login_requerido
def nuevo_producto():
    if request.method == 'POST':
        try:
            prod = Producto(
                nombre         = request.form['nombre'],
                categoria      = request.form['categoria'],
                unidad_medida  = request.form['unidad_medida'],
                cantidad_medida= float(
                    request.form['cantidad_medida']),
                variedad       = request.form.get(
                    'variedad', 'General') or 'General',
                precio_venta   = float(
                    request.form['precio_venta']),
                stock          = float(request.form['stock']),
                descripcion    = request.form.get(
                    'descripcion', ''),
                fecha_registro = datetime.now().strftime(
                    "%Y-%m-%d"))
            db.session.add(prod)
            db.session.commit()
            flash('✅ Producto registrado correctamente',
                  'success')
            return redirect(url_for('productos'))
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'error')

    return render_template('form_producto.html',
                           producto=None,
                           titulo='➕ Nuevo Producto')

@app.route('/productos/editar/<int:id>',
           methods=['GET', 'POST'])
@login_requerido
def editar_producto(id):
    prod = Producto.query.get_or_404(id)
    if request.method == 'POST':
        try:
            prod.nombre          = request.form['nombre']
            prod.categoria       = request.form['categoria']
            prod.unidad_medida   = request.form['unidad_medida']
            prod.cantidad_medida = float(
                request.form['cantidad_medida'])
            prod.variedad        = request.form.get(
                'variedad', 'General') or 'General'
            prod.precio_venta    = float(
                request.form['precio_venta'])
            prod.stock           = float(request.form['stock'])
            prod.descripcion     = request.form.get(
                'descripcion', '')
            db.session.commit()
            flash('✅ Producto actualizado', 'success')
            return redirect(url_for('productos'))
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'error')

    return render_template('form_producto.html',
                           producto=prod,
                           titulo='✏️ Editar Producto')

@app.route('/productos/eliminar/<int:id>')
@login_requerido
def eliminar_producto(id):
    prod = Producto.query.get_or_404(id)
    prod.activo = False
    db.session.commit()
    flash('✅ Producto eliminado', 'success')
    return redirect(url_for('productos'))

@app.route('/api/productos')
@login_requerido
def api_productos():
    prods = Producto.query.filter(
        Producto.activo == True,
        Producto.stock  >  0
    ).order_by(Producto.nombre).all()
    return jsonify([{
        'id'           : p.id,
        'nombre'       : p.nombre,
        'variedad'     : p.variedad,
        'precio_venta' : p.precio_venta,
        'stock'        : p.stock,
        'unidad_medida': p.unidad_medida
    } for p in prods])

# ══════════════════════════════════════════════
#              VENTAS
# ══════════════════════════════════════════════
@app.route('/ventas')
@login_requerido
def ventas():
    desde = request.args.get(
        'desde', datetime.now().strftime("%Y-%m-%d"))
    hasta = request.args.get(
        'hasta', datetime.now().strftime("%Y-%m-%d"))

    lista = Venta.query.filter(
        Venta.fecha >= desde,
        Venta.fecha <= hasta
    ).order_by(Venta.id.desc()).all()

    total_periodo = sum(
        v.total for v in lista if not v.anulada)

    return render_template('ventas.html',
        ventas        = lista,
        desde         = desde,
        hasta         = hasta,
        total_periodo = total_periodo)

@app.route('/ventas/nueva', methods=['GET', 'POST'])
@login_requerido
def nueva_venta():
    if request.method == 'POST':
        data = request.get_json()
        try:
            venta = Venta(
                fecha          = datetime.now().strftime(
                    "%Y-%m-%d"),
                hora           = datetime.now().strftime(
                    "%H:%M:%S"),
                cliente_nombre = data.get(
                    'cliente', 'Público General'),
                usuario_id     = session['usuario_id'],
                total          = data['total'],
                observaciones  = data.get('observaciones', ''))
            db.session.add(venta)
            db.session.flush()

            for item in data['items']:
                det = DetalleVenta(
                    venta_id        = venta.id,
                    producto_id     = item['producto_id'],
                    cantidad        = item['cantidad'],
                    precio_unitario = item['precio'],
                    subtotal        = item['subtotal'])
                db.session.add(det)

                prod = Producto.query.get(item['producto_id'])
                if prod:
                    prod.stock -= item['cantidad']

            db.session.commit()
            return jsonify({
                'success' : True,
                'venta_id': venta.id,
                'mensaje' : f'Venta #{venta.id:04d} registrada'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error'  : str(e)
            })

    clientes = Cliente.query.filter_by(
        activo=True).order_by(Cliente.nombre).all()
    return render_template('nueva_venta.html',
                           clientes=clientes)

@app.route('/ventas/detalle/<int:id>')
@login_requerido
def detalle_venta(id):
    venta = Venta.query.get_or_404(id)
    return render_template('detalle_venta.html',
                           venta=venta)

@app.route('/ventas/anular/<int:id>')
@login_requerido
def anular_venta(id):
    venta = Venta.query.get_or_404(id)
    if not venta.anulada:
        for det in venta.detalles:
            prod = Producto.query.get(det.producto_id)
            if prod:
                prod.stock += det.cantidad
        venta.anulada = True
        db.session.commit()
        flash(f'✅ Venta #{id:04d} anulada y stock restaurado',
              'success')
    return redirect(url_for('ventas'))

# ══════════════════════════════════════════════
#              COMPRAS
# ══════════════════════════════════════════════
@app.route('/compras')
@login_requerido
def compras():
    desde = request.args.get(
        'desde', datetime.now().strftime("%Y-%m-%d"))
    hasta = request.args.get(
        'hasta', datetime.now().strftime("%Y-%m-%d"))

    lista = Compra.query.filter(
        Compra.fecha >= desde,
        Compra.fecha <= hasta
    ).order_by(Compra.id.desc()).all()

    insumos = Insumo.query.filter_by(
        activo=True).order_by(Insumo.nombre).all()

    total = sum(c.precio_total for c in lista)

    return render_template('compras.html',
        compras = lista,
        insumos = insumos,
        desde   = desde,
        hasta   = hasta,
        total   = total)

@app.route('/compras/nueva', methods=['POST'])
@login_requerido
def nueva_compra():
    try:
        insumo_id       = int(request.form['insumo_id'])
        cantidad        = float(request.form['cantidad'])
        precio_unitario = float(request.form['precio_unitario'])

        compra = Compra(
            fecha           = datetime.now().strftime("%Y-%m-%d"),
            hora            = datetime.now().strftime("%H:%M:%S"),
            insumo_id       = insumo_id,
            cantidad        = cantidad,
            precio_unitario = precio_unitario,
            precio_total    = cantidad * precio_unitario,
            proveedor       = request.form.get(
                'proveedor', 'No especificado'),
            observaciones   = request.form.get(
                'observaciones', ''))
        db.session.add(compra)

        insumo = Insumo.query.get(insumo_id)
        if insumo:
            insumo.stock += cantidad

        db.session.commit()
        flash('✅ Compra registrada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {str(e)}', 'error')

    return redirect(url_for('compras'))

@app.route('/insumos/nuevo', methods=['POST'])
@login_requerido
def nuevo_insumo():
    try:
        insumo = Insumo(
            nombre        = request.form['nombre'],
            unidad_medida = request.form['unidad_medida'],
            stock_minimo  = float(
                request.form.get('stock_minimo', 5)))
        db.session.add(insumo)
        db.session.commit()
        flash('✅ Insumo registrado', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
    return redirect(url_for('compras'))

# ══════════════════════════════════════════════
#              CLIENTES
# ══════════════════════════════════════════════
@app.route('/clientes')
@login_requerido
def clientes():
    buscar = request.args.get('buscar', '')
    if buscar:
        lista = Cliente.query.filter(
            Cliente.activo == True,
            db.or_(
                Cliente.nombre.ilike(f'%{buscar}%'),
                Cliente.telefono.ilike(f'%{buscar}%')
            )).order_by(Cliente.nombre).all()
    else:
        lista = Cliente.query.filter_by(
            activo=True).order_by(Cliente.nombre).all()
    return render_template('clientes.html',
                           clientes=lista,
                           buscar=buscar)

@app.route('/clientes/nuevo', methods=['POST'])
@login_requerido
def nuevo_cliente():
    try:
        cliente = Cliente(
            nombre         = request.form['nombre'],
            telefono       = request.form.get('telefono', ''),
            direccion      = request.form.get('direccion', ''),
            email          = request.form.get('email', ''),
            fecha_registro = datetime.now().strftime("%Y-%m-%d"))
        db.session.add(cliente)
        db.session.commit()
        flash('✅ Cliente registrado', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
    return redirect(url_for('clientes'))

@app.route('/clientes/editar/<int:id>',
           methods=['GET', 'POST'])
@login_requerido
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        cliente.nombre    = request.form['nombre']
        cliente.telefono  = request.form.get('telefono', '')
        cliente.direccion = request.form.get('direccion', '')
        cliente.email     = request.form.get('email', '')
        db.session.commit()
        flash('✅ Cliente actualizado', 'success')
        return redirect(url_for('clientes'))
    return render_template('form_cliente.html',
                           cliente=cliente)

# ══════════════════════════════════════════════
#              REPORTES
# ══════════════════════════════════════════════
@app.route('/reportes')
@login_requerido
def reportes():
    desde = request.args.get('desde',
        (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"))
    hasta = request.args.get('hasta',
        datetime.now().strftime("%Y-%m-%d"))

    ventas_p  = Venta.query.filter(
        Venta.fecha >= desde,
        Venta.fecha <= hasta,
        Venta.anulada == False).all()
    total_v   = sum(v.total for v in ventas_p)

    compras_p = Compra.query.filter(
        Compra.fecha >= desde,
        Compra.fecha <= hasta).all()
    total_c   = sum(c.precio_total for c in compras_p)

    ganancia  = total_v - total_c

    from sqlalchemy import func
    mas_vendidos = db.session.query(
        Producto.nombre,
        Producto.variedad,
        Producto.unidad_medida,
        func.sum(DetalleVenta.cantidad).label('total_cant'),
        func.sum(DetalleVenta.subtotal).label('total_venta')
    ).join(DetalleVenta).join(Venta).filter(
        Venta.fecha    >= desde,
        Venta.fecha    <= hasta,
        Venta.anulada  == False
    ).group_by(Producto.id).order_by(
        func.sum(DetalleVenta.subtotal).desc()
    ).limit(10).all()

    ventas_diarias = db.session.query(
        Venta.fecha,
        func.count(Venta.id).label('num'),
        func.sum(Venta.total).label('total')
    ).filter(
        Venta.fecha   >= desde,
        Venta.fecha   <= hasta,
        Venta.anulada == False
    ).group_by(Venta.fecha).order_by(Venta.fecha).all()

    return render_template('reportes.html',
        desde          = desde,
        hasta          = hasta,
        total_ventas   = total_v,
        total_compras  = total_c,
        ganancia       = ganancia,
        num_ventas     = len(ventas_p),
        mas_vendidos   = mas_vendidos,
        ventas_diarias = ventas_diarias)

# ══════════════════════════════════════════════
#              INICIAR APP
# ══════════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
