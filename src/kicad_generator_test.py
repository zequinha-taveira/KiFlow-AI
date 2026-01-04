from pathlib import Path
import uuid

def generate_header():
    return '(kicad_sch (version 20211014) (generator "TextToPCB_AI")\n'

def generate_paper_settings():
    return '  (paper "A4")\n'

def generate_lib_symbols():
    # Defines a simple resistor symbol embedded in the schematic
    return """  (lib_symbols
    (symbol "Device:R" (pin_numbers hide) (pin_names (offset 0)) (in_bom yes) (on_board yes)
      (property "Reference" "R" (id 0) (at 2.032 0 90)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "R" (id 1) (at 0 0 90)
        (effects (font (size 1.27 1.27)))
      )
      (symbol "R_0_1"
        (rectangle (start -0.1905 -1.016) (end 0.1905 1.016)
          (stroke (width 0.254) (type default) (color 0 0 0 0))
          (fill (type none))
        )
      )
      (symbol "R_1_1"
        (pin passive line (at 0 2.54 270) (length 1.524)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 0 -2.54 90) (length 1.524)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
  )\n"""

def generate_component_instance(ref, val, x, y, uuid_val):
    return f"""  (symbol (lib_id "Device:R") (at {x} {y} 0) (unit 1)
    (in_bom yes) (on_board yes)
    (uuid {uuid_val})
    (property "Reference" "{ref}" (id 0) (at {x+2.032} {y} 90)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{val}" (id 1) (at {x} {y} 90)
      (effects (font (size 1.27 1.27)))
    )
  )\n"""

def generate_end():
    return ')\n'

def main():
    content = ""
    content += generate_header()
    content += generate_paper_settings()
    content += generate_lib_symbols()
    
    # Place two resistors
    content += generate_component_instance("R1", "10k", 50, 50, uuid.uuid4())
    content += generate_component_instance("R2", "220", 60, 50, uuid.uuid4())
    
    content += generate_end()
    
    output_path = Path("test_output.kicad_sch")
    with open(output_path, "w") as f:
        f.write(content)
        
    print(f"Generated {output_path}")

if __name__ == "__main__":
    main()
