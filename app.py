from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
import sqlite3
from datetime import datetime, timedelta
import os
import io
import xlsxwriter

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

def init_db():
    conn = sqlite3.connect('barberia_michael.db')
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

horarios = {
    'domingo':   ('09:00', '16:00'),
    'lunes':     ('09:00', '18:30'),
    'martes':    ('09:00', '17:00'),
    'miércoles': ('09:00', '18:30'),
    'jueves':    ('09:00', '17:00'),
    'viernes':   ('09:00', '19:00'),
    'sábado':    ('09:00', '14:00')
}

def generar_horas_disponibles(dia_semana, fecha):
    if dia_semana not in horarios:
        return []

    inicio, fin = horarios[dia_semana]
    inicio_dt = datetime.strptime(inicio, '%H:%M')
    fin_dt = datetime.strptime(fin, '%H:%M')

    conn = sqlite3.connect('barberia_michael.db')
    c = conn.cursor()
    c.execute("SELECT hora FROM citas WHERE fecha = ?", (fecha,))
    ocupadas = [h[0] for h in c.fetchall()]
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
                flash(f'El campo {campo} es obligatorio.')
                return redirect(url_for('agendar'))

        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        servicio = request.form['servicio']
        fecha = request.form['fecha']
        hora = request.form['hora']

        dia_semana = datetime.strptime(fecha, '%Y-%m-%d').strftime('%A').lower()
        dias_map = {
            'monday': 'lunes',
            'tuesday': 'martes',
            'wednesday': 'miércoles',
            'thursday': 'jueves',
            'friday': 'viernes',
            'saturday': 'sábado',
            'sunday': 'domingo'
        }
        dia_es = dias_map.get(dia_semana, '')

        horas_disp = generar_horas_disponibles(dia_es, fecha)
        if hora not in horas_disp:
            flash('La hora seleccionada ya está ocupada, por favor elige otra.')
            return redirect(url_for('agendar'))

        conn = sqlite3.connect('barberia_michael.db')
        c = conn.cursor()
        c.execute("INSERT INTO citas (nombre, email, telefono, servicio, fecha, hora) VALUES (?, ?, ?, ?, ?, ?)",
                  (nombre, email, telefono, servicio, fecha, hora))
        conn.commit()
        conn.close()

        flash('✅ Cita agendada con éxito.')
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

if __name__ == '__main__':
    if not os.path.exists('barberia_michael.db'):
        init_db()
    app.run(debug=True, host='0.0.0.0', port=10000)
