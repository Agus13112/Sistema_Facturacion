# app.py - Backend Sistema de Facturación AFIP/ARCA con Flask
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import json
import io

app = Flask(__name__)
CORS(app)

# Base de datos simulada
facturas = []
contadores = {'A': 1, 'B': 1}
puntos_venta = [1, 2, 3, 4, 5]

def generar_cae():
    """Generar CAE simulado (Código de Autorización Electrónico)"""
    return str(random.randint(10000000000000, 99999999999999))

def generar_numero_factura(tipo, punto_venta):
    """Generar número de factura con formato XXXXX-XXXXXXXX"""
    global contadores
    numero = contadores[tipo]
    contadores[tipo] += 1
    return f"{str(punto_venta).zfill(5)}-{str(numero).zfill(8)}"


def calcular_totales(items, tipo):
    importe_iva = 0.21
    """Calcular subtotal, IVA y total según tipo de factura"""
    subtotal = sum(item['cantidad'] * item['precioUnitario'] for item in items)
    
    if tipo == 'A':
        # Factura A: discrimina IVA
        iva = subtotal * importe_iva
        total = subtotal + iva
        return {
            'subtotal': round(subtotal, 2),
            'iva': round(iva, 2),
            'total': round(total, 2)
        }
    else:
        # Factura B: IVA incluido
        total = subtotal + (subtotal * importe_iva)
        subtotal_neto = total   
        iva = total - subtotal_neto
       
        return {
            'subtotal': round(subtotal_neto, 2),
            'iva': round(iva, 2),
            'total': round(total, 2) 
        }


@app.route('/api/facturas', methods=['POST'])
def crear_factura():
    """Crear nueva factura"""
    try:
        data = request.get_json()
        
        tipo = data.get('tipo')
        punto_venta = data.get('puntoVenta')
        cliente = data.get('cliente')
        items = data.get('items')
        
        # Validaciones
        if tipo not in ['A', 'B']:
            return jsonify({'error': 'Tipo de factura inválido. Debe ser A o B'}), 400
        
        if punto_venta not in puntos_venta:
            return jsonify({'error': 'Punto de venta inválido'}), 400
        
        if not items or len(items) == 0:
            return jsonify({'error': 'Debe incluir al menos un item'}), 400
        
        # Generar factura
        totales = calcular_totales(items, tipo)
        fecha = datetime.now()
        
        factura = {
            'id': len(facturas) + 1,
            'tipo': tipo,
            'numero': generar_numero_factura(tipo, punto_venta),
            'puntoVenta': punto_venta,
            'cae': generar_cae(),
            'fechaEmision': fecha.isoformat(),
            'fechaVencimientoCAE': (fecha + timedelta(days=10)).isoformat(),
            'cliente': cliente,
            'items': items,
            'subtotal': totales['subtotal'],
            'iva': totales['iva'],
            'total': totales['total'],
            'estado': 'Autorizada'
        }
        
        facturas.append(factura)
        
        return jsonify({
            'success': True,
            'mensaje': 'Factura autorizada correctamente',
            'factura': factura
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Error al procesar la factura: {str(e)}'}), 500

@app.route('/api/facturas', methods=['GET'])
def obtener_facturas():
    """Obtener todas las facturas con filtros opcionales"""
    tipo = request.args.get('tipo')
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    
    resultado = facturas.copy()
    
    if tipo:
        resultado = [f for f in resultado if f['tipo'] == tipo]
    
    if desde:
        fecha_desde = datetime.fromisoformat(desde)
        resultado = [f for f in resultado if datetime.fromisoformat(f['fechaEmision']) >= fecha_desde]
    
    if hasta:
        fecha_hasta = datetime.fromisoformat(hasta)
        resultado = [f for f in resultado if datetime.fromisoformat(f['fechaEmision']) <= fecha_hasta]
    
    return jsonify({
        'total': len(resultado),
        'facturas': resultado
    })

@app.route('/api/facturas/<int:id>', methods=['GET'])
def obtener_factura(id):
    """Obtener factura por ID"""
    factura = next((f for f in facturas if f['id'] == id), None)
    
    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404
    
    return jsonify(factura)

@app.route('/api/puntos-venta', methods=['GET'])
def obtener_puntos_venta():
    """Obtener puntos de venta disponibles"""
    return jsonify(puntos_venta)

@app.route('/api/verificar-cae/<cae>', methods=['GET'])
def verificar_cae(cae):
    """Verificar validez de un CAE"""
    factura = next((f for f in facturas if f['cae'] == cae), None)
    
    if not factura:
        return jsonify({
            'valido': False,
            'mensaje': 'CAE no encontrado'
        })
    
    vencido = datetime.now() > datetime.fromisoformat(factura['fechaVencimientoCAE'])
    
    return jsonify({
        'valido': not vencido,
        'factura': factura,
        'mensaje': 'CAE vencido' if vencido else 'CAE válido'
    })

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas generales"""
    total_facturado = sum(f['total'] for f in facturas)
    facturas_a = len([f for f in facturas if f['tipo'] == 'A'])
    facturas_b = len([f for f in facturas if f['tipo'] == 'B'])
    
    return jsonify({
        'totalFacturas': len(facturas),
        'facturasA': facturas_a,
        'facturasB': facturas_b,
        'totalFacturado': round(total_facturado, 2)
    })

@app.route('/', methods=['GET'])
def index():
    """Página de bienvenida"""
    return '''
    <h1>Sistema de Facturación AFIP/ARCA</h1>
    <p>API REST para facturación electrónica simulada</p>
    <h2>Endpoints disponibles:</h2>
    <ul>
        <li>POST /api/facturas - Crear nueva factura</li>
        <li>GET /api/facturas - Obtener todas las facturas</li>
        <li>GET /api/facturas/:id - Obtener factura por ID</li>
        <li>GET /api/puntos-venta - Obtener puntos de venta</li>
        <li>GET /api/verificar-cae/:cae - Verificar CAE</li>
        <li>GET /api/estadisticas - Obtener estadísticas</li>
    </ul>
    '''

if __name__ == '__main__':
    print('🚀 Servidor AFIP/ARCA corriendo en http://localhost:5000')
    print('📋 Endpoints disponibles:')
    print('   POST   /api/facturas')
    print('   GET    /api/facturas')
    print('   GET    /api/facturas/:id')
    print('   GET    /api/puntos-venta')
    print('   GET    /api/verificar-cae/:cae')
    print('   GET    /api/estadisticas')
    app.run(host="0.0.0.0", debug=True, port=5000)