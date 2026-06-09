from __future__ import annotations

import logging
from typing import Optional

import ollama
from httpx import Timeout

from config.settings import (
    PAYLOAD_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_TIMEOUT,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)

logger = logging.getLogger(__name__)


class OllamaClient:


    def __init__(

        self,

        model: str = PAYLOAD_MODEL,

        base_url: str = OLLAMA_BASE_URL,

        temperature: float = LLM_TEMPERATURE,

        max_tokens: int = LLM_MAX_TOKENS,

        timeout: float = OLLAMA_TIMEOUT

    ) -> None:


        self._model = model

        self._temperature = temperature

        self._max_tokens = max_tokens

        self._timeout_seconds = timeout


        self._timeout = Timeout(

            timeout,

            connect=5.0
        )


        self._client = ollama.Client(

            host=base_url,

            timeout=self._timeout
        )


        logger.info(

            "OllamaClient initialized "
            "(model=%s)",

            self._model
        )


    def generate(

        self,

        prompt: str,

        system: Optional[str] = None

    ) -> str:



        if not prompt or not prompt.strip():

            raise ValueError(

                "Prompt cannot be empty"
            )


        messages=[]


        if system:

            messages.append({

                "role":
                "system",

                "content":
                system
            })


        messages.append({

            "role":
            "user",

            "content":
            prompt
        })


        try:

            response=(

                self._client.chat(

                    model=
                    self._model,

                    messages=
                    messages,

                    options={

                        "temperature":self._temperature,

                        "num_predict":self._max_tokens
                    }
                )
            )


            if (

                "message"
                not in response

                or

                "content"
                not in response["message"]

            ):

                raise RuntimeError(

                    "Invalid response "
                    "received from Ollama"
                )


            return (

                response[
                    "message"
                ][
                    "content"
                ]
                .strip()
            )


        except Exception as exc:

            logger.exception(

                "Inference failure "
                "for model %s",

                self._model
            )


            raise RuntimeError(

                f"Ollama inference failed: "
                f"{str(exc)}"

            ) from exc


    def health_check(

        self

    ) -> bool:

        """
        Verify Ollama server
        and model availability.
        """

        try:

            response=(

                self._client.list()
            )


            models=[

                model["name"]

                for model in response.get(
                    "models",
                    []
                )
            ]


            model_name=(

                self._model
                .split(":")[0]
            )


            available=(

                any(

                    model_name in m

                    for m in models
                )
            )


            if not available:

                logger.warning(

                    "Model '%s' "
                    "not found. "
                    "Available=%s",

                    self._model,

                    models
                )


            return available


        except Exception as exc:

            logger.error(

                "Health check failed: %s",

                exc
            )

            return False