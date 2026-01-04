import re
from typing import List, Dict
from src.models.circuit import Circuit

class DesignValidator:
    """
    Validador interno para simular ERC (Electrical Rules Check) e DRC (Design Rules Check).
    """
    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.errors = []
        self.warnings = []

    def validate_erc(self):
        """Verifica regras elétricas básicas."""
        # 1. Floating Nets (Nets com menos de 2 nós)
        for net in self.circuit.nets:
            if len(net.nodes) < 2:
                self.warnings.append(f"ERC: Net '{net.name}' está flutuando (apenas {len(net.nodes)} conexão).")

        # 2. Pinos não conectados
        # Mapear todos os pinos conectados em nets
        connected_pins = set()
        for net in self.circuit.nets:
            for node in net.nodes:
                connected_pins.add(node) # Formato "CompID:PinNum"

        for comp in self.circuit.components:
            # Esta verificação é limitada se não soubermos quantos pinos o componente REALMENTE tem.
            # Mas podemos verificar se o componente tem alguma conexão definida no modelo.
            if not comp.connections:
                 self.errors.append(f"ERC: Componente '{comp.id}' não possui nenhuma conexão definida.")

    def validate_drc(self, pcb_content: str):
        """Verifica regras de design físico (sobreposição básica)."""
        # Extrair posições (at X Y) de cada footprint
        # Nota: Como o gerador agora usa posições dinâmicas, podemos extrair do arquivo gerado 
        # ou passar as coordenadas calculadas. Vamos tentar extrair do conteúdo gerado.
        
        comp_positions = re.findall(r'\(footprint\s+"[^"]+"\s+.*\(property\s+"Reference"\s+"([^"]+)"\s+.*\s+\(at\s+([-\d\.]+)\s+([-\d\.]+)', pcb_content)
        
        # DRC de sobreposição simplificado (raio de colisão de 5mm por padrão)
        radius = 5.0
        pos_list = []
        for ref, x, y in comp_positions:
            pos_list.append({"ref": ref, "x": float(x), "y": float(y)})

        for i, c1 in enumerate(pos_list):
            for c2 in pos_list[i+1:]:
                dist = ((c1["x"] - c2["x"])**2 + (c1["y"] - c2["y"])**2)**0.5
                if dist < radius:
                    self.errors.append(f"DRC: Possível sobreposição entre '{c1['ref']}' e '{c2['ref']}' (distância: {dist:.2f}mm).")

    def get_report(self):
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }

if __name__ == "__main__":
    from src.models.circuit import Component, Net
    test_circ = Circuit(
        project_name="Broken Test",
        description="Teste de erros",
        components=[Component(id="R1", type="Res", value="1k", library_ref="Device:R")],
        nets=[Net(name="Empty", nodes=["R1:1"])]
    )
    val = DesignValidator(test_circ)
    val.validate_erc()
    print(val.get_report())
