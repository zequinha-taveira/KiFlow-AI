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
                full_name TEXT UNIQUE,
                content TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS footprints (
                id INTEGER PRIMARY KEY,
                lib_name TEXT,
                fp_name TEXT,
                description TEXT,
                full_name TEXT UNIQUE,
                content TEXT
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
            self._parse_fp_dir(fp_dir)
        
        self.conn.commit()
    
    def _parse_fp_dir(self, fp_dir: Path):
        lib_name = fp_dir.stem
        for mod_file in fp_dir.glob("*.kicad_mod"):
            fp_name = mod_file.stem
            full_name = f"{lib_name}:{fp_name}"
            content = mod_file.read_text(encoding="utf-8", errors="ignore")
            # O arquivo .kicad_mod já é o conteúdo do footprint (começa com (footprint ...) )
            self._insert_footprint(lib_name, fp_name, full_name, content)

    def _parse_sym_file(self, file_path: Path):
        lib_name = file_path.stem
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        # Extração robusta de blocos (symbol ...)
        idx = 0
        length = len(content)
        
        while idx < length:
            start = content.find('(symbol "', idx)
            if start == -1: break
            
            name_start = start + 9
            name_end = content.find('"', name_start)
            if name_end == -1: break
            sym_name = content[name_start:name_end]
            
            balance = 0
            end = -1
            for i in range(start, length):
                if content[i] == '(': balance += 1
                elif content[i] == ')': 
                    balance -= 1
                    if balance == 0:
                        end = i + 1
                        break
            
            if end != -1:
                sym_content = content[start:end]
                if ":" not in sym_name: 
                    full_name = f"{lib_name}:{sym_name}"
                    self._insert_symbol(lib_name, sym_name, full_name, sym_content)
                idx = end
            else:
                idx = name_end

    def _insert_symbol(self, lib, name, full, content):
        try:
            self.conn.execute("""
                INSERT INTO symbols (lib_name, sym_name, full_name, content) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(full_name) DO UPDATE SET content=excluded.content
            """, (lib, name, full, content))
        except Exception as e: pass

    def _insert_footprint(self, lib, name, full, content):
        try:
            self.conn.execute("""
                INSERT INTO footprints (lib_name, fp_name, full_name, content) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(full_name) DO UPDATE SET content=excluded.content
            """, (lib, name, full, content))
        except: pass

    def search_symbol(self, query: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT full_name, lib_name, sym_name FROM symbols 
            WHERE full_name LIKE ? OR sym_name LIKE ? 
            ORDER BY (CASE WHEN sym_name = ? THEN 0 WHEN sym_name LIKE ? THEN 1 ELSE 2 END)
            LIMIT 5
        """, (f"%{query}%", f"%{query}%", query, f"{query}%"))
        return cursor.fetchall()
        
    def get_symbol_content(self, full_name: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT content FROM symbols WHERE full_name = ?", (full_name,))
        res = cursor.fetchone()
        return res[0] if res else None

    def get_footprint_content(self, full_name: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT content FROM footprints WHERE full_name = ?", (full_name,))
        res = cursor.fetchone()
        return res[0] if res else None

    def get_suggested_footprints(self, symbol_name: str):
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
    # db.scan_libs() 
    print(f"DB atualizado.")
