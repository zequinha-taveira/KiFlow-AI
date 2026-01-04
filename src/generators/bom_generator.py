import csv
import random
from src.models.circuit import Circuit

class BOMGenerator:
    """
    Gera uma lista de materiais (BOM) com dados simulados de mercado.
    """
    def generate(self, circuit: Circuit, output_file: str):
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Reference", "Value", "Footprint", "MPN (Mock)", "Estimated Price (USD)", "Market Status"])
            
            for comp in circuit.components:
                mpn, price, status = self._mock_marketplace_search(comp.library_ref, comp.value)
                writer.writerow([
                    comp.id, 
                    comp.value, 
                    comp.footprint or "N/A", 
                    mpn, 
                    f"{price:.4f}", 
                    status
                ])
        return output_file

    def _mock_marketplace_search(self, lib_ref: str, value: str):
        """Simula uma busca em APIs como Octopart/LCSC."""
        # Gerar um código MPN fictício mas realista
        prefix = lib_ref.split(":")[-1].upper()
        if not prefix: prefix = "PART"
        
        mpn = f"{prefix}-{value.replace(' ', '')}-{random.randint(100, 999)}AB"
        price = random.uniform(0.01, 0.5) # Preços de componentes passivos/discretos
        
        if "ESP32" in value.upper() or "STM32" in value.upper():
            price = random.uniform(2.0, 5.0)
            status = "In Stock"
        elif random.random() > 0.95:
             status = "Out of Stock"
             price = 0.0
        else:
            status = "In Stock"
            
        return mpn, price, status

if __name__ == "__main__":
    from src.models.circuit import Component
    test_circuit = Circuit(
        project_name="BOM Test",
        description="Teste de BOM",
        components=[
            Component(id="R1", type="Resistor", value="10k", library_ref="Device:R"),
            Component(id="U1", type="MCU", value="ESP32-WROOM", library_ref="MCU:ESP32")
        ],
        nets=[]
    )
    gen = BOMGenerator()
    gen.generate(test_circuit, "bom_test.csv")
    print("Gerado bom_test.csv")
