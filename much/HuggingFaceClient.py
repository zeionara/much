# moved to raconteur module: https://github.com/zeionara/raconteur

from enum import Enum
from os import environ as env, makedirs, path as os_path
from time import sleep

from transformers import pipeline

from requests import post

WAITING_INTERVAL = 60
N_ATTEMPTS = 5


class Task(Enum):
    SUMMARIZATION = 'summarization'
    TRANSLATION = 'translation'

    @property
    def property(self):
        match self:
            case Task.SUMMARIZATION:
                return 'summary_text'
            case Task.TRANSLATION:
                return 'translation_text'


class HuggingFaceClient:
    def __init__(
        self,
        model: str = 'IlyaGusev/rut5_base_headline_gen_telegram', task: Task = Task.SUMMARIZATION,
        token: str = None, hf_cache: str = None, local: bool = False, device: int = -1
    ):
        if token is None:
            token = env.get('HUGGING_FACE_INFERENCE_API_TOKEN')

            if token is None and not local:
                raise ValueError('Huggingface api token is required')

        self.token = token
        self.model = model
        self.task = task

        self.url = f'https://api-inference.huggingface.co/models/{model}'
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

        self.hf_cache = hf_cache
        self.local = local
        self.device = device

        if local:
            self._init_model()
        else:
            self.model = None

    def _init_model(self):
        hf_cache = self.hf_cache

        if hf_cache is not None:
            if not os_path.isdir(hf_cache):
                makedirs(hf_cache)

            _hf_cache = env.get('HF_CACHE')
            env['HF_CACHE'] = hf_cache

        self.model = pipeline(self.task.value, model = self.model, device = self.device)

        if _hf_cache is not None:
            env['HF_CACHE'] = _hf_cache

    def infer_one(self, text: str):
        if not self.local:
            raise ValueError('The client does not use a local model')

        return self.model(text)[0][self.task.property]

    def infer_many(self, texts: list[str]):
        if not self.local:
            raise ValueError('The client does not use a local model')

        return [item[self.task.property] for item in self.model(texts)]

    def summarize(self, text: str, verbose: bool = False):
        n_attempts = 0

        if self.local:
            return self.infer_one(text)

        while True:
            response = post(self.url, headers = self.headers, json = text)

            if response.status_code == 200:
                return response.json()[0][self.task.property]
            elif response.status_code == 503:
                response_json = response.json()

                if (estimated_time := response_json.get('estimated_time')) is not None:
                    if verbose:
                        print(f'The model is loading. Waiting for {estimated_time} seconds before proceeding...')
                    sleep(estimated_time)
                    if verbose:
                        print('Proceeding...')
                else:
                    if n_attempts > N_ATTEMPTS:
                        if self.model is None:
                            self._init_model()
                            self.local = True
                        return self.infer_one(text)
                        # raise ValueError(f'Unexpected error format: {response_json}')
                    else:
                        n_attempts += 1
                        sleep(WAITING_INTERVAL)
            else:
                if n_attempts > N_ATTEMPTS:
                    if self.model is None:
                        self._init_model()
                        self.local = True
                    return self.infer_one(text)
                    # raise ValueError(f'Unexpected response status code: {response.status_code}')
                else:
                    n_attempts += 1
                    sleep(WAITING_INTERVAL)
