import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config.config import Config
from util.log import Log


class S3Uploader:
    """
    Classe responsável por fazer upload de arquivos para um bucket S3.
    """

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            aws_session_token=Config.AWS_SESSION_TOKEN,  # Necessário para AWS Academy
            region_name=Config.AWS_REGION,
        )
        self.bucket_name = Config.AWS_S3_BUCKET

    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """
        Faz upload de um arquivo local para o S3.

        Args:
            local_path: Caminho do arquivo local.
            s3_key: Caminho/nome do objeto dentro do bucket S3.

        Returns:
            True se o upload for bem-sucedido, False caso contrário.
        """
        try:
            Log.info(f"[S3] Iniciando upload de '{local_path}' → s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            Log.info(f"[S3] Upload concluído com sucesso! s3://{self.bucket_name}/{s3_key}")
            return True
        except FileNotFoundError:
            Log.error(f"[S3] Arquivo '{local_path}' não encontrado para upload.")
            return False
        except NoCredentialsError:
            Log.error("[S3] Credenciais AWS não encontradas. Verifique AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env.")
            return False
        except ClientError as e:
            Log.error(f"[S3] Erro ao fazer upload: {e}")
            return False
