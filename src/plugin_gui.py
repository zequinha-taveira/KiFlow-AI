import wx
import os
import threading
from src.bridge import GenerationBridge

class AIGeneratorDialog(wx.Dialog):
    def __init__(self, parent, title="KiCad AI Generator"):
        super(AIGeneratorDialog, self).__init__(parent, title=title, size=(550, 450))
        
        self.bridge = None
        self.InitUI()
        self.Centre()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Header
        header = wx.StaticText(panel, label="Gerador de PCB a partir de Texto")
        header.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        vbox.Add(header, flag=wx.ALL, border=15)

        # Prompt Input
        self.prompt_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 120))
        self.prompt_ctrl.SetHint("Descreva seu circuito (ex: Regulador 5V com filtros)...")
        vbox.Add(self.prompt_ctrl, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=15)

        # Model Selection
        hbox_model = wx.BoxSizer(wx.HORIZONTAL)
        hbox_model.Add(wx.StaticText(panel, label="Modelo: "), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.model_choice = wx.Choice(panel, choices=["gpt-3.5-turbo", "gpt-4o", "OpenRouter", "Ollama"])
        self.model_choice.SetSelection(0)
        hbox_model.Add(self.model_choice, proportion=1)
        vbox.Add(hbox_model, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=15)

        # Status Dash (Multi-line log)
        self.status_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 80))
        self.status_log.SetBackgroundColour(wx.Colour(240, 240, 240))
        vbox.Add(self.status_log, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=15)

        # Buttons
        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_generate = wx.Button(panel, label="Gerar Hardware", size=(130, 40))
        self.btn_generate.Bind(wx.EVT_BUTTON, self.OnGenerate)
        self.btn_generate.SetBackgroundColour(wx.Colour(0, 120, 215))
        self.btn_generate.SetForegroundColour(wx.WHITE)
        
        hbox_btns.Add(self.btn_generate, flag=wx.RIGHT, border=10)
        hbox_btns.Add(wx.Button(panel, id=wx.ID_CANCEL, label="Fechar"), flag=wx.LEFT, border=10)
        
        vbox.Add(hbox_btns, flag=wx.ALIGN_RIGHT | wx.ALL, border=15)

        panel.SetSizer(vbox)

    def log(self, message):
        wx.CallAfter(self.status_log.AppendText, f"> {message}\n")

    def OnGenerate(self, event):
        prompt = self.prompt_ctrl.GetValue()
        model = self.model_choice.GetString(self.model_choice.GetSelection())
        
        if not prompt.strip():
            wx.MessageBox("Por favor, descreva o circuito.", "Aviso", wx.OK | wx.ICON_WARNING)
            return

        self.btn_generate.Disable()
        self.status_log.Clear()
        self.log(f"Iniciando pipeline com {model}...")
        
        # Inicia thread de fundo para não travar o KiCad
        thread = threading.Thread(target=self.RunGeneration, args=(prompt, model))
        thread.start()

    def RunGeneration(self, prompt, model):
        bridge = GenerationBridge(model=model)
        success, message = bridge.process(prompt, callback=self.log)
        
        wx.CallAfter(self.OnGenerationComplete, success, message)

    def OnGenerationComplete(self, success, message):
        self.btn_generate.Enable()
        if success:
            wx.MessageBox(message, "Sucesso", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(message, "Erro", wx.OK | wx.ICON_ERROR)


def main():
    app = wx.App()
    dialog = AIGeneratorDialog(None)
    dialog.ShowModal()
    dialog.Destroy()
    app.MainLoop()

if __name__ == "__main__":
    main()
