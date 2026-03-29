from openwakeword import Model
import openwakeword

openwakeword.utils.download_models()

model = Model(wakeword_models=["hey_jarvis"])

