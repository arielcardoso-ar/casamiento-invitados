#!/usr/bin/env python3
"""
Base de datos para el casamiento - SQLite
"""

import sqlite3
import json
from datetime import datetime

class CasamientoDatabase:
    def __init__(self, db_path='casamiento.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Inicializar todas las tablas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabla de presupuesto
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS presupuesto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL,
                item TEXT NOT NULL,
                estimado REAL DEFAULT 0,
                real REAL DEFAULT 0,
                pagado REAL DEFAULT 0,
                proveedor TEXT,
                notas TEXT,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de invitados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                email TEXT,
                grupo TEXT,
                invitacion_enviada BOOLEAN DEFAULT 0,
                confirmacion TEXT DEFAULT 'Pendiente',
                asiste BOOLEAN,
                menu TEXT,
                alergias TEXT,
                mesa INTEGER,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de tareas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tarea TEXT NOT NULL,
                categoria TEXT,
                prioridad TEXT,
                estado TEXT DEFAULT 'pendiente',
                responsable TEXT,
                notas TEXT,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de proveedores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL,
                nombre TEXT NOT NULL,
                contacto TEXT,
                telefono TEXT,
                email TEXT,
                direccion TEXT,
                precio TEXT,
                contratado BOOLEAN DEFAULT 0,
                notas TEXT,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de configuración
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de sincronización
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sincronizacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                accion TEXT NOT NULL,
                datos TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de fotos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT NOT NULL,
                nombre_original TEXT NOT NULL,
                ruta TEXT NOT NULL,
                thumbnail TEXT,
                subido_por TEXT,
                descripcion TEXT,
                fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ========== PRESUPUESTO ==========
    
    def get_presupuesto(self):
        """Obtener todo el presupuesto agrupado por categoría"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT categoria, item, estimado, real, pagado, proveedor, notas
            FROM presupuesto
            ORDER BY categoria, item
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Agrupar por categoría
        categorias = {}
        for row in rows:
            cat = row['categoria']
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append({
                'item': row['item'],
                'estimado': row['estimado'],
                'real': row['real'],
                'pagado': row['pagado'],
                'proveedor': row['proveedor'],
                'notas': row['notas']
            })
        
        return [{'nombre': cat, 'items': items} for cat, items in categorias.items()]
    
    def actualizar_presupuesto_item(self, categoria, item, datos):
        """Actualizar un item del presupuesto"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE presupuesto
            SET real = ?, pagado = ?, proveedor = ?, notas = ?,
                actualizado = CURRENT_TIMESTAMP
            WHERE categoria = ? AND item = ?
        ''', (
            datos.get('real', 0),
            datos.get('pagado', 0),
            datos.get('proveedor', ''),
            datos.get('notas', ''),
            categoria,
            item
        ))
        
        if cursor.rowcount == 0:
            # Si no existe, insertar
            cursor.execute('''
                INSERT INTO presupuesto (categoria, item, estimado, real, pagado, proveedor, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                categoria,
                item,
                datos.get('estimado', 0),
                datos.get('real', 0),
                datos.get('pagado', 0),
                datos.get('proveedor', ''),
                datos.get('notas', '')
            ))
        
        conn.commit()
        conn.close()
        
        self.registrar_sincronizacion('presupuesto', 'actualizar', {
            'categoria': categoria,
            'item': item,
            'datos': datos
        })
    
    # ========== INVITADOS ==========
    
    def get_invitados(self):
        """Obtener todos los invitados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nombre, telefono, email, grupo, invitacion_enviada,
                   confirmacion, asiste, menu, alergias, mesa
            FROM invitados
            ORDER BY nombre
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def agregar_invitado(self, datos):
        """Agregar un nuevo invitado"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invitados (nombre, telefono, email, grupo, invitacion_enviada,
                                  confirmacion, asiste, menu, alergias, mesa)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['nombre'],
            datos.get('telefono', ''),
            datos.get('email', ''),
            datos['grupo'],
            datos.get('invitacion_enviada', False),
            datos.get('confirmacion', 'Pendiente'),
            datos.get('asiste', None),
            datos.get('menu', ''),
            datos.get('alergias', ''),
            datos.get('mesa', None)
        ))
        
        invitado_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.registrar_sincronizacion('invitados', 'agregar', datos)
        return invitado_id
    
    def actualizar_invitado(self, invitado_id, datos):
        """Actualizar un invitado"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE invitados
            SET nombre = ?, telefono = ?, email = ?, grupo = ?,
                invitacion_enviada = ?, confirmacion = ?, asiste = ?,
                menu = ?, alergias = ?, mesa = ?,
                actualizado = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            datos['nombre'],
            datos.get('telefono', ''),
            datos.get('email', ''),
            datos['grupo'],
            datos.get('invitacion_enviada', False),
            datos.get('confirmacion', 'Pendiente'),
            datos.get('asiste', None),
            datos.get('menu', ''),
            datos.get('alergias', ''),
            datos.get('mesa', None),
            invitado_id
        ))
        
        conn.commit()
        conn.close()
        
        self.registrar_sincronizacion('invitados', 'actualizar', datos)
    
    def eliminar_invitado(self, invitado_id):
        """Eliminar un invitado"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM invitados WHERE id = ?', (invitado_id,))
        
        conn.commit()
        conn.close()
        
        self.registrar_sincronizacion('invitados', 'eliminar', {'id': invitado_id})
    
    # ========== TAREAS ==========
    
    def get_tareas(self):
        """Obtener todas las tareas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, fecha, tarea, categoria, prioridad, estado, responsable, notas
            FROM tareas
            ORDER BY 
                CASE prioridad
                    WHEN 'URGENTE' THEN 1
                    WHEN 'ALTA' THEN 2
                    WHEN 'MEDIA' THEN 3
                    ELSE 4
                END,
                fecha
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def actualizar_tarea_estado(self, tarea_id, estado):
        """Actualizar el estado de una tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tareas
            SET estado = ?, actualizado = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (estado, tarea_id))
        
        conn.commit()
        conn.close()
        
        self.registrar_sincronizacion('tareas', 'actualizar_estado', {
            'id': tarea_id,
            'estado': estado
        })
    
    # ========== PROVEEDORES ==========
    
    def get_proveedores(self):
        """Obtener todos los proveedores"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, categoria, nombre, contacto, telefono, email,
                   direccion, precio, contratado, notas
            FROM proveedores
            ORDER BY categoria, nombre
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def actualizar_proveedor_contratado(self, proveedor_id, contratado):
        """Marcar proveedor como contratado"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE proveedores
            SET contratado = ?, actualizado = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (contratado, proveedor_id))
        
        conn.commit()
        conn.close()
        
        self.registrar_sincronizacion('proveedores', 'contratar', {
            'id': proveedor_id,
            'contratado': contratado
        })
    
    # ========== CONFIGURACIÓN ==========
    
    def get_config(self, clave):
        """Obtener un valor de configuración"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,))
        row = cursor.fetchone()
        conn.close()
        
        return row['valor'] if row else None
    
    def set_config(self, clave, valor):
        """Establecer un valor de configuración"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO configuracion (clave, valor, actualizado)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (clave, valor))
        
        conn.commit()
        conn.close()
    
    # ========== SINCRONIZACIÓN ==========
    
    def registrar_sincronizacion(self, tipo, accion, datos):
        """Registrar una acción de sincronización"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sincronizacion (tipo, accion, datos)
            VALUES (?, ?, ?)
        ''', (tipo, accion, json.dumps(datos)))
        
        conn.commit()
        conn.close()
    
    def get_cambios_desde(self, timestamp):
        """Obtener cambios desde un timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tipo, accion, datos, timestamp
            FROM sincronizacion
            WHERE timestamp > ?
            ORDER BY timestamp
        ''', (timestamp,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'tipo': row['tipo'],
            'accion': row['accion'],
            'datos': json.loads(row['datos']),
            'timestamp': row['timestamp']
        } for row in rows]
    
    # ========== FOTOS ==========
    
    def agregar_foto(self, datos):
        """Agregar una nueva foto"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fotos (nombre_archivo, nombre_original, ruta, thumbnail, 
                             subido_por, descripcion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datos['nombre_archivo'],
            datos['nombre_original'],
            datos['ruta'],
            datos.get('thumbnail', ''),
            datos.get('subido_por', 'Invitado'),
            datos.get('descripcion', '')
        ))
        
        foto_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return foto_id
    
    def get_fotos(self):
        """Obtener todas las fotos"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nombre_archivo, nombre_original, ruta, thumbnail,
                   subido_por, descripcion, fecha_subida
            FROM fotos
            ORDER BY fecha_subida DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def eliminar_foto(self, foto_id):
        """Eliminar una foto"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM fotos WHERE id = ?', (foto_id,))
        
        conn.commit()
        conn.close()

if __name__ == '__main__':
    # Inicializar base de datos
    db = CasamientoDatabase()
    print("✓ Base de datos inicializada correctamente")
