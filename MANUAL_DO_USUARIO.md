# Manual do Usuário - AI Hardware Generator

## 1. Introdução
O **AI Hardware Generator** é uma ferramenta que utiliza Inteligência Artificial para automatizar as etapas iniciais de design eletrônico no KiCad, transformando descrições em linguagem natural em projetos completos.

## 2. Instalação

### Pré-requisitos
*   **Python 3.10+** instalado no PATH.
*   **KiCad 7.0 ou 8.0**.
*   Dependências Python: `pip install PySide6 openai jinja2 pydantic requests click`.

### Configuração do Plugin no KiCad
1.  Copie o arquivo `ai_gen_plugin.py` e a pasta `src` para o diretório de plugins do KiCad:
    *   **Windows**: `%APPDATA%\kicad\8.0\scripting\plugins`
2.  Reinicie o KiCad ou vá em "Tools -> External Plugins -> Refresh Plugins".

## 3. Como Usar

### Via Interface Desktop (Recomendado)
1.  Abra o KiCad PCBNew.
2.  Clique no ícone **🚀 AI Hardware Generator** na barra de ferramentas superior.
3.  Na janela que se abre:
    *   **Prompt**: Descreva seu circuito (ex: "Um carregador de bateria Li-po com proteção").
    *   **Modelo de IA**: Selecione **AUTO** para que o sistema escolha o melhor provedor.
    *   **Gerar Projeto**: O console mostrará o progresso e criará os arquivos na pasta atual.

### Via Linha de Comando (CLI)
Para desenvolvedores, use o comando:
```bash
python -m src.cli generate "Descrição do hardware"
```

## 4. Configuração de Variáveis de Ambiente
Para usar modelos específicos, configure as seguintes chaves de API:
*   `OPENAI_API_KEY`: Para modelos GPT-4o.
*   `OPENROUTER_API_KEY`: Para acesso a modelos como Claude 3.5.
*   `LLM_BASE_URL`: Configure como `http://localhost:11434/v1` para usar **Ollama** localmente.

## 5. Arquivos Gerados
*   `.kicad_pro`: Arquivo de projeto (abrir este no KiCad).
*   `.kicad_sch`: Esquemático completo com conexões.
*   `.kicad_pcb`: Layout inicial com componentes agrupados.
*   `.ipc`: Netlist industrial para validação.
*   `.dsn`: Arquivo para roteamento automático no Freerouting.

## 6. Limitações Conhecidas
*   O sistema não realiza o roteamento final das trilhas (deve ser feito manualmente ou via Freerouting).
*   Circuitos de altíssima complexidade (ex: placas de 8 camadas) podem exigir refinamento manual significativo.
