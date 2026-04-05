#!/bin/bash

# Este script cria toda a infraestrutura na AWS usando o AWS CLI.
# Certifique-se de que suas credenciais estão configuradas no seu ambiente:
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN

echo "Iniciando o deploy da infraestrutura..."

# Variáveis
REGION="us-east-1"
BRONZE_BUCKET="bronze-gp02"
SILVER_BUCKET="silver-gp02"
GOLD_BUCKET="gold-gp02"
LAMBDA_SILVER_NAME="bronze-to-silver"
LAMBDA_GOLD_NAME="silver-to-gold"
RUNTIME="python3.12"
LAYER_ARN="arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python314:2"

echo "Obtendo o ID da conta AWS (isso valida suas credenciais)..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ $? -ne 0 ]; then
    echo "Erro: Não foi possível obter o Account ID. Suas credenciais AWS expiraram ou não foram configuradas."
    exit 1
fi

ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/LabRole"
echo "Usando Role: $ROLE_ARN"

echo "1. Criando buckets S3..."
aws s3api create-bucket --bucket $BRONZE_BUCKET --region $REGION > /dev/null
aws s3api create-bucket --bucket $SILVER_BUCKET --region $REGION > /dev/null
aws s3api create-bucket --bucket $GOLD_BUCKET --region $REGION > /dev/null
echo "Buckets criados."

echo "2. Empacotando o código das funções Lambda..."
# Salva o diretório atual
CURRENT_DIR=$(pwd)
cd ../lambda

# Compacta os arquivos usando Python para garantir compatibilidade no Windows
python -c "import zipfile; zipfile.ZipFile('lambda_silver.zip', mode='w').write('lambda_function.py')"
python -c "import zipfile; zipfile.ZipFile('lambda_gold.zip', mode='w').write('lambda_gold.py')"
cd "$CURRENT_DIR"
echo "Código empacotado."

echo "3. Criando Lambda: $LAMBDA_SILVER_NAME..."
aws lambda create-function \
    --function-name $LAMBDA_SILVER_NAME \
    --runtime $RUNTIME \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://../lambda/lambda_silver.zip \
    --timeout 30 \
    --layers $LAYER_ARN \
    --region $REGION > /dev/null || echo "Aviso: Lambda $LAMBDA_SILVER_NAME pode já existir."

echo "4. Criando Lambda: $LAMBDA_GOLD_NAME..."
aws lambda create-function \
    --function-name $LAMBDA_GOLD_NAME \
    --runtime $RUNTIME \
    --role $ROLE_ARN \
    --handler lambda_gold.lambda_handler \
    --zip-file fileb://../lambda/lambda_gold.zip \
    --timeout 30 \
    --layers $LAYER_ARN \
    --region $REGION > /dev/null || echo "Aviso: Lambda $LAMBDA_GOLD_NAME pode já existir."

# Aguarda as Lambdas estarem prontas antes de colocar triggers
sleep 5

echo "5. Adicionando permissões para o S3 invocar as Lambdas..."
aws lambda add-permission \
    --function-name $LAMBDA_SILVER_NAME \
    --principal s3.amazonaws.com \
    --statement-id AllowS3BronzeInvoke \
    --action "lambda:InvokeFunction" \
    --source-arn arn:aws:s3:::$BRONZE_BUCKET \
    --region $REGION > /dev/null 2>&1

aws lambda add-permission \
    --function-name $LAMBDA_GOLD_NAME \
    --principal s3.amazonaws.com \
    --statement-id AllowS3SilverInvoke \
    --action "lambda:InvokeFunction" \
    --source-arn arn:aws:s3:::$SILVER_BUCKET \
    --region $REGION > /dev/null 2>&1

echo "6. Configurando S3 Event Notifications..."
cat <<EOF > bronze_trigger.json
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$LAMBDA_SILVER_NAME",
      "Events": ["s3:ObjectCreated:Put"],
      "Filter": {
        "Key": {
          "FilterRules": [
            { "Name": "prefix", "Value": "bronze/stories_bronze_" },
            { "Name": "suffix", "Value": ".csv" }
          ]
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-notification-configuration \
    --bucket $BRONZE_BUCKET \
    --notification-configuration file://bronze_trigger.json \
    --region $REGION

cat <<EOF > silver_trigger.json
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$LAMBDA_GOLD_NAME",
      "Events": ["s3:ObjectCreated:Put"],
      "Filter": {
        "Key": {
          "FilterRules": [
            { "Name": "prefix", "Value": "silver/stories_silver_" },
            { "Name": "suffix", "Value": ".csv" }
          ]
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-notification-configuration \
    --bucket $SILVER_BUCKET \
    --notification-configuration file://silver_trigger.json \
    --region $REGION

echo "Limpando arquivos temporários..."
rm bronze_trigger.json silver_trigger.json

echo "✅ Infraestrutura implantada com sucesso na AWS!"
