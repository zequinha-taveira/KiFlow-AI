import os
import re
from pathlib import Path
import sqlite3
from typing import Optional

class ComponentDB:
    """
    Indexador de componentes KiCad. Escaneia arquivos .kicad_sym e .kicad_mod.
    """
    def __init__(self, db_path: str = "components.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                lib_name TEXT,
                sym_name TEXT,
                description TEXT,
                keywords TEXT,
                full_name TEXT UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS footprints (
                id INTEGER PRIMARY KEY,
                lib_name TEXT,
                fp_name TEXT,
                description TEXT,
                full_name TEXT UNIQUE
            )
        """)
        self.conn.commit()

    def scan_libs(self, libs_dir: str = "libs"):
        """
        Escaneia a pasta libs em busca de símbolos e footprints.
        """
        libs_path = Path(libs_dir)
        if not libs_path.exists():
            print(f"Diretório {libs_dir} não encontrado.")
            return

        print("Lendo símbolos...")
        for sym_file in libs_path.rglob("*.kicad_sym"):
            self._parse_sym_file(sym_file)
            
        print("Lendo footprints...")
        for fp_dir in libs_path.rglob("*.pretty"):
            lib_name = fp_dir.stem
            for mod_file in fp_dir.glob("*.kicad_mod"):
                fp_name = mod_file.stem
                full_name = f"{lib_name}:{fp_name}"
                self._insert_footprint(lib_name, fp_name, full_name)
        
        self.conn.commit()

    def _parse_sym_file(self, file_path: Path):
        lib_name = file_path.stem
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        # Regex básico para extrair nomes de símbolos (simplificado)
        symbols = re.findall(r'\(symbol "([^"]+)"', content)
        for sym_name in symbols:
            # Pula símbolos que começam com a biblioteca para evitar duplicatas de hierarquia
            if ":" in sym_name: continue 
            full_name = f"{lib_name}:{sym_name}"
            self._insert_symbol(lib_name, sym_name, full_name)

    def _insert_symbol(self, lib, name, full):
        try:
            self.conn.execute("INSERT OR IGNORE INTO symbols (lib_name, sym_name, full_name) VALUES (?, ?, ?)", 
                             (lib, name, full))
        except: pass

    def _insert_footprint(self, lib, name, full):
        try:
            self.conn.execute("INSERT OR IGNORE INTO footprints (lib_name, fp_name, full_name) VALUES (?, ?, ?)", 
                             (lib, name, full))
        except: pass

    def search_symbol(self, query: str):
        cursor = self.conn.cursor()
        # Busca inteligente: busca no nome do símbolo ou biblioteca
        cursor.execute("""
            SELECT full_name, lib_name, sym_name FROM symbols 
            WHERE full_name LIKE ? OR sym_name LIKE ? 
            ORDER BY (CASE WHEN sym_name = ? THEN 0 WHEN sym_name LIKE ? THEN 1 ELSE 2 END)
            LIMIT 5
        """, (f"%{query}%", f"%{query}%", query, f"{query}%"))
        return cursor.fetchall()

    def get_suggested_footprints(self, symbol_name: str):
        """
        Tenta sugerir footprints baseados no nome do componente.
        """
        cursor = self.conn.cursor()
        query = ""
        if "Resistor" in symbol_name or symbol_name.endswith(":R"):
            query = "Resistor_SMD:R_0805_2012Metric"
        elif "LED" in symbol_name:
            query = "LED_SMD:LED_0805_2012Metric"
        elif "Capacitor" in symbol_name or symbol_name.endswith(":C"):
            query = "Capacitor_SMD:C_0805_2012Metric"
        
        if query:
            cursor.execute("SELECT full_name FROM footprints WHERE full_name = ?", (query,))
            res = cursor.fetchone()
            return [res[0]] if res else []
        
        return []

if __name__ == "__main__":
    db = ComponentDB()
    db.scan_libs()
    print(f"Indexação concluída.")
    results = db.search_symbol("Resistor")
    print(f"Resultados para 'Resistor': {results}")
