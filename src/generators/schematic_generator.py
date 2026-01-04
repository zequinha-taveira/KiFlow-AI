import uuid
from jinja2 import Environment, FileSystemLoader
from src.models.circuit import Circuit
from pathlib import Path

class SchematicGenerator:
    BASIC_SYMBOLS = {
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

    def generate(self, circuit: Circuit, output_file: str):
        # Mapeamento de pinos padrão (offset em relação ao centro do componente)
        # Device:R tem pino 1 em (0, -2.54) e pino 2 em (0, 2.54) [Vertical default]
        pin_map = {
            "Device:R": {"1": (0, -3.81), "2": (0, 3.81)},
            "Device:LED": {"1": (0, -2.54), "2": (0, 2.54)},
            "Device:C": {"1": (0, -2.54), "2": (0, 2.54)},
        }

        # Preparar dados para o template
        components_data = []
        comp_instances = {}
        
        for i, comp in enumerate(circuit.components):
            x, y = 100 + (i * 30), 100
            comp_info = {
                "id": comp.id,
                "library_ref": comp.library_ref,
                "value": comp.value,
                "x": x,
                "y": y,
                "uuid": str(uuid.uuid4())
            }
            components_data.append(comp_info)
            comp_instances[comp.id] = comp_info

        wires = []
        labels = []
        
        # Gerar fios para as conexões
        for net in circuit.nets:
            if len(net.nodes) < 2:
                # Se só tem um nó, colocar uma label para facilitar futuras conexões
                node = net.nodes[0]
                comp_id, pin_num = node.split(":")
                if comp_id in comp_instances:
                    c = comp_instances[comp_id]
                    # Offset do pino
                    offsets = pin_map.get(c["library_ref"], {"1": (0, 0)})
                    off_x, off_y = offsets.get(pin_num, (0, 0))
                    labels.append({
                        "name": net.name,
                        "x": c["x"] + off_x,
                        "y": c["y"] + off_y,
                        "angle": 0,
                        "uuid": str(uuid.uuid4())
                    })
                continue

            # Conectar os nós da net
            prev_point = None
            for node in net.nodes:
                comp_id, pin_num = node.split(":")
                if comp_id in comp_instances:
                    c = comp_instances[comp_id]
                    offsets = pin_map.get(c["library_ref"], {"1": (0, 0)})
                    off_x, off_y = offsets.get(pin_num, (0, 0))
                    curr_point = (c["x"] + off_x, c["y"] + off_y)
                    
                    if prev_point:
                        # Criar fio entre os pontos
                        wires.append({
                            "x1": prev_point[0], "y1": prev_point[1],
                            "x2": curr_point[0], "y2": curr_point[1],
                            "uuid": str(uuid.uuid4())
                        })
                    prev_point = curr_point

        used_symbols = set()
        for comp in circuit.components:
            if comp.library_ref in self.BASIC_SYMBOLS:
                used_symbols.add(self.BASIC_SYMBOLS[comp.library_ref])

        render_data = {
            "project_uuid": str(uuid.uuid4()),
            "components": components_data,
            "lib_symbols": list(used_symbols), 
            "wires": wires,
            "labels": labels
        }

        content = self.template.render(render_data)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_file

if __name__ == "__main__":
    from src.models.circuit import Circuit, Component, Net, PinConnection
    
    # Teste rápido
    test_circuit = Circuit(
        project_name="Test Gen",
        description="Teste de geração",
        components=[
            Component(id="R1", type="Res", value="1k", library_ref="Device:R")
        ],
        nets=[]
    )
    
    gen = SchematicGenerator()
    gen.generate(test_circuit, "gen_test.kicad_sch")
    print("Gerado gen_test.kicad_sch")
