from jinja2 import Environment, FileSystemLoader
from src.models.circuit import Circuit

class FirmwareGenerator:
    """
    Gera código boilerplate baseado nos pinos usados no hardware.
    """
    def __init__(self, template_path: str = "src/generators"):
        self.env = Environment(loader=FileSystemLoader(template_path))
        self.template = self.env.get_template("firmware_template.j2")

    def generate(self, circuit: Circuit, output_file: str):
        # 1. Tentar identificar mapeamentos de pinos úteis (ex: conexões para um MCU)
        pin_mappings = []
        
        # Estratégia simples: procurar redes que conectam a pinos de componentes com nomes tipo 'IO', 'GPIO', 'D', 'A'
        # ou componentes microcontroladores.
        
        for net in circuit.nets:
            if len(net.nodes) >= 2:
                # Se uma net conecta um componente 'U' (MCU) a algo tipo 'LED' ou 'SW'
                mcu_node = None
                peripheral_node = None
                
                for node in net.nodes:
                    comp_id = node.split(":")[0]
                    if comp_id.startswith("U"): 
                        mcu_node = node
                    else:
                        peripheral_node = node
                
                if mcu_node and peripheral_node:
                    mcu_pad = mcu_node.split(":")[1]
                    periph_id = peripheral_node.split(":")[0]
                    
                    # Nome amigável: PIN_LED1 ou PIN_GND (se for GND)
                    name = f"PIN_{periph_id}_{net.name.upper()}"
                    # Limpar nome de caracteres inválidos em C++
                    name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
                    
                    pin_mappings.append({
                        "name": name,
                        "pin": mcu_pad, # Simplificação: usa o número do pad como pino real
                        "comp_id": periph_id,
                        "pad": peripheral_node.split(":")[1]
                    })

        render_data = {
            "project_name": circuit.project_name,
            "description": circuit.description,
            "pin_mappings": pin_mappings
        }

        content = self.template.render(render_data)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_file

if __name__ == "__main__":
    from src.models.circuit import Component, Net, PinConnection
    test_circ = Circuit(
        project_name="Blink Lite",
        description="LED no GPIO 4",
        components=[
            Component(id="U1", type="MCU", value="ESP32", library_ref="MCU:ESP32", 
                      connections=[PinConnection(pin_number="4", net_name="LED_NET")]),
            Component(id="D1", type="LED", value="Red", library_ref="Device:LED",
                      connections=[PinConnection(pin_number="2", net_name="LED_NET")])
        ],
        nets=[Net(name="LED_NET", nodes=["U1:4", "D1:2"])]
    )
    gen = FirmwareGenerator()
    gen.generate(test_circ, "firmware_test.ino")
    print("Gerado firmware_test.ino")
