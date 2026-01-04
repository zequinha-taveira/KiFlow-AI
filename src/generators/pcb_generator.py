import uuid
import re
import math
import random
from jinja2 import Environment, FileSystemLoader
from src.models.circuit import Circuit
from src.component_db import ComponentDB
from pathlib import Path

class PCBGenerator:
    FALLBACK_FOOTPRINT = """(footprint "Fallback:Resistor" (layer "F.Cu")
  (property "Reference" "{ref}" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{val}" (at 0 2 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (attr smd)
  (fp_line (start -1 -1) (end 1 -1) (layer "F.SilkS") (width 0.12))
  (fp_line (start 1 -1) (end 1 1) (layer "F.SilkS") (width 0.12))
  (fp_line (start 1 1) (end -1 1) (layer "F.SilkS") (width 0.12))
  (fp_line (start -1 1) (end -1 -1) (layer "F.SilkS") (width 0.12))
  (pad "1" smd rect (at -1.5 0) (size 1 1.5) (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "2" smd rect (at 1.5 0) (size 1 1.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)"""

    def __init__(self, template_path: str = "src/generators"):
        self.env = Environment(loader=FileSystemLoader(template_path))
        self.template = self.env.get_template("pcb_template.j2")
        self.db = ComponentDB()

    def _inject_nets_into_footprint(self, content: str, comp_id: str, connections: list, net_map: dict) -> str:
        pin_net_info = {}
        for conn in connections:
            if conn.net_name in net_map:
                pin_net_info[conn.pin_number] = (net_map[conn.net_name], conn.net_name)

        def replace_pad(match):
            full_pad_str = match.group(0)
            pin_match = re.search(r'\(pad\s+"?([^"\s]+)"?', full_pad_str)
            if not pin_match: return full_pad_str
            
            pin_num = pin_match.group(1)
            if pin_num in pin_net_info:
                net_id, net_name = pin_net_info[pin_num]
                return full_pad_str[:-1] + f' (net {net_id} "{net_name}"))'
            return full_pad_str

        new_content = ""
        idx = 0
        length = len(content)
        while idx < length:
            start = content.find('(pad ', idx)
            if start == -1:
                new_content += content[idx:]; break
            new_content += content[idx:start]
            balance, end = 0, -1
            for i in range(start, length):
                if content[i] == '(': balance += 1
                elif content[i] == ')':
                    balance -= 1
                    if balance == 0: end = i + 1; break
            if end != -1:
                pad_block = content[start:end]
                modified_block = replace_pad(re.match(r'.*', pad_block))
                new_content += modified_block
                idx = end
            else:
                new_content += content[start:]; break
        return new_content

    def _run_physics_sim(self, components, nets):
        """Simulação de grafos de força para posicionar componentes."""
        # Inicialização
        coords = {c.id: {"x": random.uniform(50, 150), "y": random.uniform(50, 150)} for c in components}
        velocities = {c.id: {"x": 0.0, "y": 0.0} for c in components}
        
        # Parâmetros
        iterations = 50
        repulsion = 400.0
        attraction = 0.05
        damping = 0.8
        
        # Conexões (adjacência ponderada pelo número de caminhos entre componentes)
        adj = {}
        for net in nets:
            nodes = [n.split(":")[0] for n in net.nodes]
            for i, c1 in enumerate(nodes):
                for c2 in nodes[i+1:]:
                    if c1 == c2: continue
                    pair = tuple(sorted((c1, c2)))
                    adj[pair] = adj.get(pair, 0) + 1

        for _ in range(iterations):
            forces = {c.id: {"x": 0.0, "y": 0.0} for c in components}
            
            # 1. Repulsão (Evitar sobreposição)
            for i, c1 in enumerate(components):
                for c2 in components[i+1:]:
                    dx = coords[c1.id]["x"] - coords[c2.id]["x"]
                    dy = coords[c1.id]["y"] - coords[c2.id]["y"]
                    dist_sq = dx*dx + dy*dy + 0.1
                    force = repulsion / dist_sq
                    
                    forces[c1.id]["x"] += (dx / math.sqrt(dist_sq)) * force
                    forces[c1.id]["y"] += (dy / math.sqrt(dist_sq)) * force
                    forces[c2.id]["x"] -= (dx / math.sqrt(dist_sq)) * force
                    forces[c2.id]["y"] -= (dy / math.sqrt(dist_sq)) * force
            
            # 2. Atração (Manter conectados próximos)
            for (c1_id, c2_id), weight in adj.items():
                dx = coords[c1_id]["x"] - coords[c2_id]["x"]
                dy = coords[c1_id]["y"] - coords[c2_id]["y"]
                dist = math.sqrt(dx*dx + dy*dy)
                
                fx = dx * attraction * weight
                fy = dy * attraction * weight
                
                forces[c1_id]["x"] -= fx
                forces[c1_id]["y"] -= fy
                forces[c2_id]["x"] += fx
                forces[c2_id]["y"] += fy
            
            # 3. Atualizar posições
            for c in components:
                velocities[c.id]["x"] = (velocities[c.id]["x"] + forces[c.id]["x"]) * damping
                velocities[c.id]["y"] = (velocities[c.id]["y"] + forces[c.id]["y"]) * damping
                
                # Limite de velocidade para evitar "explosões"
                v_mag = math.sqrt(velocities[c.id]["x"]**2 + velocities[c.id]["y"]**2)
                if v_mag > 10.0:
                    velocities[c.id]["x"] *= 10.0 / v_mag
                    velocities[c.id]["y"] *= 10.0 / v_mag
                
                coords[c.id]["x"] += velocities[c.id]["x"]
                coords[c.id]["y"] += velocities[c.id]["y"]
        
        return coords

    def generate(self, circuit: Circuit, output_file: str):
        # 1. Map Nets
        net_names = sorted(list(set(net.name for net in circuit.nets)))
        net_map = {name: i+1 for i, name in enumerate(net_names)}
        nets_data = [{"id": i+1, "name": name} for i, name in enumerate(net_names)]

        # 2. Physics Simulation
        final_coords = self._run_physics_sim(circuit.components, circuit.nets)

        # 3. Prepare Footprints
        footprints_data = []
        min_x, min_y = 1000, 1000
        max_x, max_y = -1000, -1000

        for comp in circuit.components:
            pos = final_coords[comp.id]
            x, y = pos["x"], pos["y"]
            
            min_x = min(min_x, x); max_x = max(max_x, x)
            min_y = min(min_y, y); max_y = max(max_y, y)

            fp_content = self.db.get_footprint_content(comp.footprint or comp.library_ref)
            if not fp_content:
                sugg = self.db.get_suggested_footprints(comp.library_ref)
                if sugg: fp_content = self.db.get_footprint_content(sugg[0])
            if not fp_content:
                fp_content = self.FALLBACK_FOOTPRINT.format(ref=comp.id, val=comp.value)
            
            final_content = self._inject_nets_into_footprint(fp_content, comp.id, comp.connections, net_map)
            
            # Atualizar posição e UUID
            final_content = re.sub(r'\(at\s+[-\d\.]+\s+[-\d\.]+\s*([-\d\.]*)\)', f'(at {x} {y} \\1)', final_content, count=1)
            final_content = re.sub(r'\(layer\s+"[^"]+"\)', f'\\g<0> (uuid {str(uuid.uuid4())})', final_content, count=1)

            footprints_data.append({"content": final_content})

        # 4. Geometry (Edge.Cuts)
        margin = 10
        b_x1, b_y1 = min_x - margin, min_y - margin
        b_x2, b_y2 = max_x + margin, max_y + margin
        
        drawings = [
            f'(gr_line (start {b_x1} {b_y1}) (end {b_x2} {b_y1}) (layer "Edge.Cuts") (width 0.1))',
            f'(gr_line (start {b_x2} {b_y1}) (end {b_x2} {b_y2}) (layer "Edge.Cuts") (width 0.1))',
            f'(gr_line (start {b_x2} {b_y2}) (end {b_x1} {b_y2}) (layer "Edge.Cuts") (width 0.1))',
            f'(gr_line (start {b_x1} {b_y2}) (end {b_x1} {b_y1}) (layer "Edge.Cuts") (width 0.1))',
        ]

        render_data = {
            "project_uuid": str(uuid.uuid4()),
            "footprints": footprints_data,
            "nets": nets_data,
            "drawings": drawings
        }

        content = self.template.render(render_data)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        return output_file

if __name__ == "__main__":
    from src.models.circuit import Circuit, Component, Net, PinConnection
    test_circuit = Circuit(
        project_name="Physics Test",
        description="Layout dinâmico",
        components=[
            Component(id="R1", type="Res", value="1k", library_ref="Device:R", connections=[PinConnection(pin_number="1", net_name="N1")]),
            Component(id="R2", type="Res", value="1k", library_ref="Device:R", connections=[PinConnection(pin_number="1", net_name="N1")]),
            Component(id="D1", type="LED", value="Red", library_ref="Device:LED", connections=[PinConnection(pin_number="1", net_name="N2")]),
        ],
        nets=[Net(name="N1", nodes=["R1:1", "R2:1"]), Net(name="N2", nodes=["D1:1"])]
    )
    gen = PCBGenerator()
    gen.generate(test_circuit, "physics_test.kicad_pcb")
    print("Gerado physics_test.kicad_pcb")
