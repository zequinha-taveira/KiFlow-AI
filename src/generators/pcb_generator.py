import uuid
from jinja2 import Environment, FileSystemLoader
from src.models.circuit import Circuit
from pathlib import Path

class PCBGenerator:
    def __init__(self, template_path: str = "src/generators"):
        self.env = Environment(loader=FileSystemLoader(template_path))
        self.template = self.env.get_template("pcb_template.j2")

    def generate(self, circuit: Circuit, output_file: str):
        # Mapeamento simples de footprints
        default_footprints = {
            "Device:R": "Resistor_SMD:R_0805_2012Metric",
            "Device:LED": "LED_SMD:LED_0805_2012Metric",
            "Device:C": "Capacitor_SMD:C_0805_2012Metric",
        }

        # Algoritmo de Clustering Básico:
        # 1. Identificar grupos de componentes altamente conectados
        # 2. Posicionar componentes do mesmo grupo próximos
        
        footprints_data = []
        placed_comps = set()
        
        # Encontra conexões (quem está ligado a quem)
        adj = {c.id: set() for c in circuit.components}
        for net in circuit.nets:
            nodes_in_net = [n.split(":")[0] for n in net.nodes]
            for i, c1 in enumerate(nodes_in_net):
                for c2 in nodes_in_net[i+1:]:
                    if c1 != c2:
                        adj[c1].add(c2)
                        adj[c2].add(c1)

        # Posicionamento por "Nuvens"
        start_x, start_y = 100, 100
        cluster_spacing = 25
        comp_spacing = 10
        
        current_x, current_y = start_x, start_y
        
        for i, comp in enumerate(circuit.components):
            if comp.id in placed_comps: continue
            
            # Novo cluster (BFS para encontrar componentes conectados)
            queue = [comp.id]
            cluster = []
            while queue:
                cid = queue.pop(0)
                if cid not in placed_comps:
                    placed_comps.add(cid)
                    cluster.append(cid)
                    for neighbor in adj.get(cid, []):
                        if neighbor not in placed_comps:
                            queue.append(neighbor)
            
            # Posiciona os componentes do cluster em um pequeno bloco
            for j, cid in enumerate(cluster):
                c_obj = next(c for c in circuit.components if c.id == cid)
                fp_ref = c_obj.footprint or default_footprints.get(c_obj.library_ref, "Resistor_SMD:R_0805_2012Metric")
                
                # Layout dentro do cluster
                offset_x = (j % 3) * comp_spacing
                offset_y = (j // 3) * comp_spacing
                
                footprints_data.append({
                    "id": cid,
                    "library_ref": fp_ref,
                    "value": c_obj.value,
                    "x": current_x + offset_x,
                    "y": current_y + offset_y,
                    "angle": 0,
                    "uuid": str(uuid.uuid4())
                })
            
            # Move para a próxima posição de cluster
            current_x += cluster_spacing
            if current_x > 200:
                current_x = start_x
                current_y += cluster_spacing


        render_data = {
            "project_uuid": str(uuid.uuid4()),
            "footprints": footprints_data
        }

        content = self.template.render(render_data)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_file

if __name__ == "__main__":
    from src.models.circuit import Circuit, Component
    
    # Teste rápido de geração de PCB
    test_circuit = Circuit(
        project_name="Test PCB",
        description="Teste de layout",
        components=[
            Component(id="R1", type="Res", value="1k", library_ref="Device:R"),
            Component(id="D1", type="LED", value="Red", library_ref="Device:LED")
        ],
        nets=[]
    )
    
    gen = PCBGenerator()
    gen.generate(test_circuit, "gen_test.kicad_pcb")
    print("Gerado gen_test.kicad_pcb")
