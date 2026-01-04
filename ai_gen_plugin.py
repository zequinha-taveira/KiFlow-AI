import pcbnew
import os
import sys
import subprocess

# Adiciona o diretório do plugin ao path para encontrar as dependências
plugin_dir = os.path.dirname(__file__)

class AIGeneratorPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "AI Hardware Generator"
        self.category = "Automation"
        self.description = "Gera esquemáticos e PCBs a partir de linguagem natural usando IA"
        self.show_toolbar_button = True 
        self.icon_file_name = os.path.join(plugin_dir, 'icon.png')

    def Run(self):
        # Localiza o executável python do sistema para rodar a GUI PySide6
        # Assume-se que as dependências estão no ambiente atual
        python_exe = sys.executable
        gui_script = os.path.join(plugin_dir, "src", "gui.py")
        
        try:
            # Lança a aplicação desktop em um processo separado
            # Define o PYTHONPATH para garantir que o 'src' seja encontrado
            env = os.environ.copy()
            env["PYTHONPATH"] = plugin_dir
            
            subprocess.Popen([python_exe, gui_script], env=env)
            pcbnew.Refresh() # Refresh para atualizar a visão se necessário
        except Exception as e:
            import wx
            wx.MessageBox(f"Erro ao lançar o gerador AI: {str(e)}", "AI Hardware Generator", wx.OK | wx.ICON_ERROR)

# Registra o plugin no KiCad
AIGeneratorPlugin().register()

