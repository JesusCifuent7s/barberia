from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
import sqlite3
from datetime import datetime, timedelta
import os
import io
import xlsxwriter

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Crear base de datos si no existe
def init_db():
    conn = sqlite3.connect('citasbarber.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            telefono TEXT NOT NULL,
            servicio TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Horarios disponibles por día
horarios = {
    'domingo':   ('09:00', '16:00'),
    'lunes':     ('09:00', '18:30'),
    'martes':    ('09:00', '17:00'),
    'miércoles': ('09:00', '18:30'),
    'jueves':    ('09:00', '17:00'),
    'viernes':   ('09:00', '19:00'),
    'sábado':    ('09:00', '14:00')
}

# Generar horas disponibles para un día y fecha
def generar_horas_disponibles(dia_semana, fecha):
    if dia_semana not in horarios:
        return []

    inicio, fin = horarios[dia_semana]
    inicio_dt = datetime.strptime(inicio, '%H:%M')
    fin_dt = datetime.strptime(fin, '%H:%M')

    # Obtener horas ya agendadas para esa fecha
    conn = sqlite3.connect('citasbarber.db')
    c = conn.cursor()
    c.execute("SELECT hora FROM citas WHERE fecha = ?", (fecha,))
    ocupadas = [datetime.strptime(h[0], "%H:%M").strftime("%H:%M") for h in c.fetchall()]
    conn.close()

    horas_disponibles = []
    actual = inicio_dt
    while actual <= fin_dt:
        hora_str = actual.strftime('%H:%M')
        if hora_str not in ocupadas:
            horas_disponibles.append(hora_str)
        actual += timedelta(minutes=30)

    return horas_disponibles

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    if request.method == 'POST':
        campos = ['nombre', 'email', 'telefono', 'servicio', 'fecha', 'hora']
        for campo in campos:
            if campo not in request.form or request.form[campo].strip() == '':
                flash(f'El campo "{campo}" es obligatorio.')
                return redirect(url_for('agendar'))

        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        servicio = request.form['servicio']
        fecha = request.form['fecha']
        hora = request.form['hora']

        conn = sqlite3.connect('citasbarber.db')
        c = conn.cursor()
        c.execute("INSERT INTO citas (nombre, email, telefono, servicio, fecha, hora) VALUES (?, ?, ?, ?, ?, ?)",
                  (nombre, email, telefono, servicio, fecha, hora))
        conn.commit()
        conn.close()

        flash('Cita agendada con éxito.')
        return redirect(url_for('index'))

    return render_template('agendar.html')

@app.route('/horas_disponibles', methods=['POST'])
def horas_disponibles():
    data = request.get_json()
    fecha = data.get('fecha')
    if not fecha:
        return jsonify([])

    dia_semana_eng = datetime.strptime(fecha, '%Y-%m-%d').strftime('%A').lower()
    dias_map = {
        'monday': 'lunes',
        'tuesday': 'martes',
        'wednesday': 'miércoles',
        'thursday': 'jueves',
        'friday': 'viernes',
        'saturday': 'sábado',
        'sunday': 'domingo'
    }
    dia_semana = dias_map.get(dia_semana_eng, '')
    disponibles = generar_horas_disponibles(dia_semana, fecha)
    return jsonify(disponibles)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        if usuario == 'admin' and clave == '1234':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            flash('Credenciales incorrectas.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Sesión cerrada.')
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('citasbarber.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM citas ORDER BY fecha, hora")
    citas = c.fetchall()
    conn.close()
    return render_template('admin.html', citas=citas)

@app.route('/eliminar_cita/<int:id>', methods=['POST'])
def eliminar_cita(id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('citasbarber.db')
    c = conn.cursor()
    c.execute("DELETE FROM citas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Cita eliminada.')
    return redirect(url_for('admin'))

@app.route('/exportar_citas')
def exportar_citas():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('citasbarber.db')
    c = conn.cursor()
    c.execute("SELECT nombre, email, telefono, servicio, fecha, hora FROM citas ORDER BY fecha, hora")
    datos = c.fetchall()
    conn.close()

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Citasbarber")

    headers = ['Nombre', 'Email', 'Teléfono', 'Servicio', 'Fecha', 'Hora']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    for row_num, fila in enumerate(datos, start=1):
        for col_num, valor in enumerate(fila):
            worksheet.write(row_num, col_num, valor)

    workbook.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="citasbarber.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    init_db()  # Se asegura que la base y tabla existan
    app.run(debug=False, host='0.0.0.0', port=10000)
