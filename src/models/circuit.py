from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class PinConnection(BaseModel):
    pin_number: str
    net_name: str

class Component(BaseModel):
    id: str = Field(..., description="ID único do componente, ex: R1, U1")
    type: str = Field(..., description="Tipo do componente, ex: Resistor, MCU")
    value: str = Field(..., description="Valor do componente, ex: 10k, STM32F103")
    library_ref: str = Field(..., description="Referência na biblioteca KiCad, ex: Device:R")
    footprint: Optional[str] = Field(None, description="Footprint associado, ex: Resistor_SMD:R_0805_2012Metric")
    connections: List[PinConnection] = Field(default_factory=list)

class Net(BaseModel):
    name: str
    nodes: List[str] = Field(..., description="Lista de ComponentID:PinNumber, ex: ['R1:1', 'U1:5']")

class Circuit(BaseModel):
    project_name: str
    description: str
    mermaid: Optional[str] = Field(None, description="Diagrama de blocos em formato Mermaid")
    components: List[Component]
    nets: List[Net]

if __name__ == "__main__":
    # Exemplo de JSON que a IA deve gerar
    example = Circuit(
        project_name="Led Blink",
        description="Um circuito simples com LED e resistor",
        components=[
            Component(
                id="R1", type="Resistor", value="220", library_ref="Device:R",
                connections=[
                    PinConnection(pin_number="1", net_name="VCC"),
                    PinConnection(pin_number="2", net_name="net_led")
                ]
            ),
            Component(
                id="D1", type="LED", value="Red", library_ref="Device:LED",
                connections=[
                    PinConnection(pin_number="1", net_name="net_led"),
                    PinConnection(pin_number="2", net_name="GND")
                ]
            )
        ],
        nets=[
            Net(name="VCC", nodes=["R1:1"]),
            Net(name="net_led", nodes=["R1:2", "D1:1"]),
            Net(name="GND", nodes=["D1:2"])
        ]
    )
    print(example.model_dump_json(indent=2))
