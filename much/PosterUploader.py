from enum import Enum

# from rr.util import is_video, is_image

from .VkPhotoUploader import VkPhotoUploader
from .VkVideoUploader import VkVideoUploader


class AttachmentType(Enum):
    PHOTO = 'photo'
    VIDEO = 'video'
    AUDIO = 'audio'
    DOCUMENT = 'doc'

    def encode(self, owner: int = None, key: int = None):
        if key is None or owner is None:
            return None

        return f'{self.value}{owner}_{key}'


class PosterUploader:
    def __init__(self, photo_uploader: VkPhotoUploader = None, video_uploader: VkVideoUploader = None):
        self.photo_uploader = VkPhotoUploader.make() if photo_uploader is None else photo_uploader
        self.video_uploader = VkVideoUploader.make() if video_uploader is None else video_uploader

    def upload(self, path: str, caption: str, description: str, verbose: bool = False):
        if is_image(path):
            return self.photo_uploader.upload(path, description, verbose), AttachmentType.PHOTO

        if is_video(path):
            return self.video_uploader.upload(path, caption, description, verbose), AttachmentType.VIDEO

        raise ValueError(f'Can\'t infer poster media type: {path}')
