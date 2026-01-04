import uuid
import re
from jinja2 import Environment, FileSystemLoader
from src.models.circuit import Circuit
from src.component_db import ComponentDB
from pathlib import Path

class SchematicGenerator:
    FALLBACK_SYMBOLS = {
        "Device:R": """    (symbol "Device:R" (pin_numbers hide) (pin_names (offset 0)) (in_bom yes) (on_board yes)
      (property "Reference" "R" (id 0) (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "R" (id 1) (at 0 0 90) (effects (font (size 1.27 1.27))))
      (symbol "R_0_1" (rectangle (start -1.016 -2.54) (end 1.016 2.54) (stroke (width 0.254) (type default) (color 0 0 0 0)) (fill (type none))))
      (symbol "R_1_1" 
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )""",
        "Device:LED": """    (symbol "Device:LED" (pin_numbers hide) (pin_names (offset 0)) (in_bom yes) (on_board yes)
      (property "Reference" "D" (id 0) (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "LED" (id 1) (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "LED_0_1" (polyline (pts (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27) (xy -1.27 -1.27)) (stroke (width 0.254) (type default) (color 0 0 0 0)) (fill (type none))))
      (symbol "LED_1_1" 
        (pin passive line (at 0 -2.54 90) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 2.54 270) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )"""
    }

    def __init__(self, template_path: str = "src/generators"):
        self.env = Environment(loader=FileSystemLoader(template_path))
        self.template = self.env.get_template("schematic_template.j2")
        self.db = ComponentDB()

    def _parse_pin_positions(self, symbol_content: str):
        """Extrai posições dos pinos para conectar os fios corretamente."""
        pins = {}
        # Pattern para pegar (pin ... (at X Y R) ... (number "N" ...)
        # Simplificado para pegar at e number
        # Nota: pins podem estar em sub-unidades (symbol "Name_1_1" ...
        
        # Estratégia: Encontrar todos os blocos (pin ...) e extrair 'at' e 'number'
        pin_blocks = re.finditer(r'\(pin\s+[^)]+\s+\(at\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\)', symbol_content)
        
        # Mapear posições por número de pino. 
        # CUIDADO: O regex acima é frágil se houver quebra de linha dentro do (at
        # Melhor iterar linha a linha ou usar blocos maiores, mas vamos tentar um regex mais guloso
        
        full_pins = re.findall(r'\(pin\s+.*?\)', symbol_content, re.DOTALL)
        
        for p_str in full_pins:
            at_match = re.search(r'\(at\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\)', p_str)
            num_match = re.search(r'\(number\s+"([^"]+)"', p_str)
            
            if at_match and num_match:
                x, y, angle = map(float, at_match.groups())
                num = num_match.group(1)
                pins[num] = (x, y)
                
        return pins

    def generate(self, circuit: Circuit, output_file: str):
        components_data = []
        comp_instances = {}
        used_symbols = {} # Map full_name -> content

        # 1. Preparar Componentes
        for i, comp in enumerate(circuit.components):
            x, y = 100 + (i * 30), 100
            
            # Tenta buscar no DB
            sym_content = self.db.get_symbol_content(comp.library_ref)
            if not sym_content:
                sym_content = self.FALLBACK_SYMBOLS.get(comp.library_ref)
            
            if sym_content:
                used_symbols[comp.library_ref] = sym_content
            
            # Descobrir pinagem para wires
            pin_offsets = self._parse_pin_positions(sym_content) if sym_content else {}
            # Fallback de pinagem se falhar o parse ou não tiver conteúdo
            if not pin_offsets:
                 pin_offsets = {"1": (0, -2.54), "2": (0, 2.54)} # Default vertical

            comp_info = {
                "id": comp.id,
                "library_ref": comp.library_ref,
                "value": comp.value,
                "x": x,
                "y": y,
                "uuid": str(uuid.uuid4()),
                "pin_offsets": pin_offsets
            }
            components_data.append(comp_info)
            comp_instances[comp.id] = comp_info

        wires = []
        labels = []
        
        # 2. Gerar Fios
        for net in circuit.nets:
            if len(net.nodes) < 2:
                # Label para nó único
                node = net.nodes[0]
                comp_id, pin_num = node.split(":")
                if comp_id in comp_instances:
                    c = comp_instances[comp_id]
                    off_x, off_y = c["pin_offsets"].get(str(pin_num), (0, 0))
                    
                    # Correção de coordenadas (KiCad Y cresce para baixo)
                    # O "at" do pino é relativo. Para (at 0 -2.54) significa acima do centro.
                    # Mas no esquemático, se o símbolo for desenhado normal, é somar.
                    
                    labels.append({
                        "name": net.name,
                        "x": c["x"] + off_x,
                        "y": c["y"] + off_y,
                        "angle": 0,
                        "uuid": str(uuid.uuid4())
                    })
                continue

            # Conectar nós em série (Simples Daisy Chain)
            # Todo: Melhorar roteamento (Manhattan)
            points = []
            for node in net.nodes:
                comp_id, pin_num = node.split(":")
                if comp_id in comp_instances:
                    c = comp_instances[comp_id]
                    off_x, off_y = c["pin_offsets"].get(str(pin_num), (0, 0))
                    points.append((c["x"] + off_x, c["y"] + off_y))
            
            # Criar segmentos de fio
            for k in range(len(points) - 1):
                p1 = points[k]
                p2 = points[k+1]
                wires.append({
                    "x1": p1[0], "y1": p1[1],
                    "x2": p2[0], "y2": p2[1],
                    "uuid": str(uuid.uuid4())
                })

        render_data = {
            "project_uuid": str(uuid.uuid4()),
            "components": components_data,
            "lib_symbols": list(used_symbols.values()), 
            "wires": wires,
            "labels": labels
        }

        content = self.template.render(render_data)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_file

if __name__ == "__main__":
    from src.models.circuit import Circuit, Component, Net
    
    # Teste rápido
    test_circuit = Circuit(
        project_name="Test Gen",
        description="Teste de geração",
        components=[
            Component(id="R1", type="Res", value="1k", library_ref="Device:R"),
            Component(id="D1", type="LED", value="Green", library_ref="Device:LED")
        ],
        nets=[]
    )
    
    gen = SchematicGenerator()
    gen.generate(test_circuit, "gen_test.kicad_sch")
    print("Gerado gen_test.kicad_sch")
