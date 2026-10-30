import json
from types import SimpleNamespace
import sys
import types
# Stub local: el test verifica la integración con una API simulada, sin red.
try:
    import openai as sdk
    if not hasattr(sdk, 'OpenAI'):
        raise ImportError
except ImportError:
    sdk = types.ModuleType('openai')
    for nombre in ('AuthenticationError', 'PermissionDeniedError', 'RateLimitError',
                   'APITimeoutError', 'APIConnectionError', 'BadRequestError',
                   'NotFoundError', 'APIStatusError'):
        setattr(sdk, nombre, type(nombre, (Exception,), {}))
    sdk.OpenAI = object
    sys.modules['openai'] = sdk
import ai


def test_genera_diez_preguntas_con_una_solicitud(monkeypatch):
    from test_core import preguntas
    llamadas=[]
    data = preguntas()
    class FakeCompletions:
        def create(self,**kwargs):
            llamadas.append(kwargs)
            return SimpleNamespace(model='gpt-4.1-mini', usage=SimpleNamespace(prompt_tokens=150,completion_tokens=250),
                choices=[SimpleNamespace(message=SimpleNamespace(refusal=None,content=json.dumps(data)),finish_reason='stop')])
    class FakeClient:
        def __init__(self,**kwargs):
            assert kwargs['api_key']=='fake_for_test'
            self.chat=SimpleNamespace(completions=FakeCompletions())
        def close(self):pass
    monkeypatch.setattr(ai,'OpenAI',FakeClient)
    registro={}
    r=ai.generar_preguntas('fake_for_test',registro)
    assert len(r)==10 and len(llamadas)==1
    assert registro['tokens_entrada']==150
    assert registro['tokens_salida']==250
    assert llamadas[0]['store'] is False
    assert llamadas[0]['model']=='gpt-4.1-mini'
