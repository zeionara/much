from requests import post


TIMEOUT = 3600


def upload_audio(path: str, title: str, artist: str, token: str, token_owner: int, audio_owner: int, api_version: str):
    response = post(
        url = 'https://api.vk.com/method/audio.getUploadServer',
        data = {
            'access_token': token,
            'v': api_version
        },
        timeout = TIMEOUT
    )

    if response.status_code == 200:
        upload_url = response.json()['response']['upload_url']

        with open(path, 'rb') as file:
            response = post(
                url = upload_url,
                files = {
                    'file': (path, file)
                },
                timeout = TIMEOUT
            )

        if response.status_code == 200:
            response_json = response.json()

            audio = response_json['audio']
            server = response_json['server']
            hash_ = response_json['hash']

            response = post(
                url = 'https://api.vk.com/method/audio.save',
                data = {
                    'access_token': token,
                    'audio': audio,
                    'server': server,
                    'hash': hash_,
                    'v': api_version,
                    'artist': artist,
                    'title': title
                },
                timeout = TIMEOUT
            )

            if response.status_code == 200:
                response_json = response.json()['response']

                if audio_owner is not None and token_owner != audio_owner:
                    response = post(
                        url = 'https://api.vk.com/method/audio.add',
                        data = {
                            'access_token': token,
                            'audio_id': (audio_id := response_json['id']),
                            'owner_id': (owner_id := response_json['owner_id']),
                            'group_id': abs(audio_owner),
                            'v': api_version
                        },
                        timeout = TIMEOUT
                    )

                    if response.status_code == 200:
                        final_audio_id = response.json().get('response')

                        response = post(
                            url = 'https://api.vk.com/method/audio.delete',
                            data = {
                                'audio_id': audio_id,
                                'owner_id': owner_id,
                                'access_token': token,
                                'v': api_version
                            },
                            timeout = TIMEOUT
                        )

                        if response.status_code == 200:
                            # print(response.json())
                            return final_audio_id
                        else:
                            raise ValueError(f'Unexpected response from server when deleting audio from the user\'s list: {response.content}')
                    else:
                        raise ValueError(f'Unexpected response from server when adding audio to the group: {response.content}')
            else:
                raise ValueError(f'Unexpected response from server when saving uploaded audio: {response.content}')
        else:
            raise ValueError(f'Unexpected response from server when uploading audio: {response.content}')
    else:
        raise ValueError(f'Unexpected response from server when obtaining upload url: {response.content}')
