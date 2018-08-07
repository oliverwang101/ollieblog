import json
import requests
from flask_babel import _
from app import current_app

def translate(text, source_language, dest_language):
    #takes the text to translate and the source and destination language codes as arguments, 
    #and it returns a string with the translated text
    if 'MS_TRANSLATOR_KEY' not in current_app.config or \
            not current_app.config['MS_TRANSLATOR_KEY']:
        return _('Error: the translation service is not configured.')
    #export MS_TRANSLATOR_KEY=183ce4b59ce54b4d95649ad2884b3261
    auth = {'Ocp-Apim-Subscription-Key': current_app.config['MS_TRANSLATOR_KEY']}
    # dict of MS receiving end key name
    r = requests.get('https://api.microsofttranslator.com/v2/Ajax.svc'
                    '/Translate?text={}&from={}&to={}'.format(
                        text, source_language, dest_language),
                    headers=auth)
    if r.status_code != 200:
        return _('Error: the translation service failed.')
    return json.loads(r.content.decode('utf-8-sig'))
