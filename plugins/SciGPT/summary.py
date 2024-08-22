import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from config import conf
from common.log import logger
import os
import html


def _change_url(url):
    if url.startswith("http://mp.weixin."):
        # 升级成https
        url = url.replace("http://mp.weixin.", "https://mp.weixin.")
    return url


class Summary:
    def __init__(self):
        pass

    def summary_url(self, sender_id: str = "sender_id", url: str = "not_url", parse_type: int = 0):
        url = _change_url(url)
        multipart_data = MultipartEncoder(
            fields={
                "sender_id": sender_id,
                "url": url,
                "title": url,
                "parse_type": str(parse_type)
            }
        )

        # 设置请求头
        headers = self.headers()
        headers['Content-Type'] = multipart_data.content_type

        # 发送 POST 请求
        url = self.base_url() + "/v1/knowledge_base/wechat_upload"
        res = requests.post(url, headers=headers, data=multipart_data, timeout=(5, 300), verify=False)

        return self._parse_summary_res(res)

    def summary(self, file_path: str, sender_id: str = "sender_id", url: str = "not_url", parse_type: int = 0):
        # 创建 MultipartEncoder 对象，包含文件和其他表单数据
        title = file_path.split('/')[-1]
        with open(file_path, "rb") as file:
            multipart_data = MultipartEncoder(
                fields={
                    "files": (title, file, "application/octet-stream"),
                    "sender_id": sender_id,
                    "url": url,
                    "title": title,
                    "parse_type": str(parse_type)
                }
            )

            # 设置请求头
            headers = self.headers()
            headers['Content-Type'] = multipart_data.content_type

            # 发送 POST 请求
            url = self.base_url() + "/v1/knowledge_base/wechat_upload"
            res = requests.post(url, headers=headers, data=multipart_data, timeout=(5, 300), verify=False)

            return self._parse_summary_res(res)

    def _parse_summary_res(self, res):
        print('res_json', res.json())
        if res.status_code == 200:
            res_json = res.json()
            logger.debug(f"[SciGPT] url summary, res={res_json}")
            data = res_json.get("data")
            docId = data.get("name_id")[0]["docId"]
            return docId
        else:
            res_json = res.json()
            logger.error(f"[SciGPT] summary error, status_code={res.status_code}, msg={res_json.get('message')}")
            return None

    def base_url(self):
        return conf().get("scigpt_api_base", "https://inplat.drugflow.com/api")

    def headers(self):
        return {"Authorization": "Bearer " + conf().get("scigpt_api_key")}

    def check_file(self, file_path: str) -> bool:
        file_size = os.path.getsize(file_path) // 1000

        # if (conf().get("max_file_size") and file_size > conf().get("max_file_size")):
        #     logger.warn(f"[SciGPT] file size exceeds limit, No processing, file_size={file_size}KB")
        #     return False

        suffix = file_path.split(".")[-1]
        support_list = ["pdf"]
        if suffix not in support_list:
            logger.warn(f"[SciGPT] unsupported file, suffix={suffix}, support_list={support_list}")
            return False

        return True

    def check_url(self, url: str):
        if not url:
            return False
        if url.startswith('http://') or url.startswith('https://'):
            return True
        return False
        # support_list = ["http://mp.weixin.qq.com", "https://mp.weixin.qq.com"]
        # black_support_list = ["https://mp.weixin.qq.com/mp/waerrpage"]
        # for black_url_prefix in black_support_list:
        #     if url.strip().startswith(black_url_prefix):
        #         logger.warn(f"[SciGPT] unsupported url, no need to process, url={url}")
        #         return False
        # for support_url in support_list:
        #     if url.strip().startswith(support_url):
        #         return True
        # return False
