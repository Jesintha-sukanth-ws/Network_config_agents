import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any

import fitz


class DocumentParser:

    SUPPORTED_METADATA=[

        "VENDOR",
        "VERSION",
        "OS",
        "TOPIC",
        "FEATURE"
    ]


    METADATA_PATTERN=re.compile(

        rf"^(?P<key>{'|'.join(SUPPORTED_METADATA)}):\s*(?P<value>.*)$",

        re.IGNORECASE
    )


    def parse(
        self,
        pdf_path:Path
    )->List[Dict[str,Any]]:

        document=fitz.open(
            str(pdf_path)
        )

        blocks=[]
        global_metadata={}
        seen_hashes=set()


        try:

            for page_num,page in enumerate(
                document,
                start=1
            ):

                for block in page.get_text(
                    "blocks",
                    sort=True
                ):

                    raw_text=(
                        block[4]
                        if len(block)>4
                        else ""
                    )

                    text=re.sub(
                        r"\s+",
                        " ",
                        raw_text
                    ).strip()


                    if not text:
                        continue


                    match=(
                        self.METADATA_PATTERN.match(
                            text
                        )
                    )


                    if match:

                        global_metadata[
                            match.group(
                                "key"
                            ).upper()
                        ]=match.group(
                            "value"
                        ).strip()

                        continue


                    if len(text)<10:
                        continue


                    content_hash=hashlib.sha256(

                        text.encode(
                            "utf-8"
                        )

                    ).hexdigest()


                    if content_hash in seen_hashes:
                        continue


                    seen_hashes.add(
                        content_hash
                    )


                    blocks.append({

                        "content":
                        text,

                        "metadata":{

                            **global_metadata,

                            "page":
                            page_num,

                            "source":
                            pdf_path.name
                        },

                        "hash":
                        content_hash
                    })


            return blocks


        finally:

            document.close()



class ChunkingService:


    def __init__(
        self,
        chunk_size=1000,
        overlap=200
    ):

        self._chunk_size=chunk_size
        self._overlap=overlap


    def split_text(
        self,
        text:str
    )->List[str]:


        if len(text)<=self._chunk_size:

            return [text]


        chunks=[]
        start=0

        delimiters=[

            "!",
            "\n\n",
            "\n",
            " "
        ]


        while start < len(text):

            end=start+self._chunk_size


            if end>=len(text):

                chunks.append(

                    text[start:]
                    .strip()

                )

                break


            split_point=-1


            for d in delimiters:

                split_point=text.rfind(
                    d,
                    start,
                    end
                )

                if split_point>start:
                    break


            if split_point<=start:

                split_point=end


            chunks.append(

                text[
                    start:split_point
                ].strip()
            )


            new_start=max(

                split_point
                -
                self._overlap,

                0
            )


            if new_start<=start:

                new_start=split_point


            start=new_start


        return [

            c
            for c in chunks
            if c
        ]