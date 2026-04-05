terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# As credenciais são lidas automaticamente das variáveis de ambiente:
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
provider "aws" {
  region = var.aws_region
}

# ── S3 Buckets ────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "bronze" {
  bucket        = "bronze-gp02"
  force_destroy = true

  tags = { Name = "bronze-gp02", Camada = "Bronze" }
}

resource "aws_s3_bucket" "silver" {
  bucket        = "silver-gp02"
  force_destroy = true

  tags = { Name = "silver-gp02", Camada = "Silver" }
}

resource "aws_s3_bucket" "gold" {
  bucket        = "gold-gp02"
  force_destroy = true

  tags = { Name = "gold-gp02", Camada = "Gold" }
}

# ── Empacota o código das Lambdas em .zip ─────────────────────────────────────

data "archive_file" "lambda_silver_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/lambda_function.py"
  output_path = "${path.module}/lambda_silver.zip"
}

data "archive_file" "lambda_gold_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/lambda_gold.py"
  output_path = "${path.module}/lambda_gold.zip"
}

# ── Lambda: bronze-to-silver ──────────────────────────────────────────────────

resource "aws_lambda_function" "bronze_to_silver" {
  function_name    = "bronze-to-silver"
  role             = var.lab_role_arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.python_runtime
  filename         = data.archive_file.lambda_silver_zip.output_path
  source_code_hash = data.archive_file.lambda_silver_zip.output_base64sha256
  timeout          = 30
  layers           = [var.pandas_layer_arn]

  tags = { Nome = "bronze-to-silver", Camada = "Silver" }
}

# Permissão para o bucket bronze invocar a Lambda
resource "aws_lambda_permission" "allow_bronze_invoke" {
  statement_id  = "AllowS3BronzeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bronze_to_silver.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.bronze.arn
}

# Trigger S3 → Lambda bronze-to-silver
resource "aws_s3_bucket_notification" "bronze_trigger" {
  bucket = aws_s3_bucket.bronze.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.bronze_to_silver.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "bronze/stories_bronze_"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_bronze_invoke]
}

# ── Lambda: silver-to-gold ────────────────────────────────────────────────────

resource "aws_lambda_function" "silver_to_gold" {
  function_name    = "silver-to-gold"
  role             = var.lab_role_arn
  handler          = "lambda_gold.lambda_handler"
  runtime          = var.python_runtime
  filename         = data.archive_file.lambda_gold_zip.output_path
  source_code_hash = data.archive_file.lambda_gold_zip.output_base64sha256
  timeout          = 30
  layers           = [var.pandas_layer_arn]

  tags = { Nome = "silver-to-gold", Camada = "Gold" }
}

# Permissão para o bucket silver invocar a Lambda
resource "aws_lambda_permission" "allow_silver_invoke" {
  statement_id  = "AllowS3SilverInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.silver_to_gold.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.silver.arn
}

# Trigger S3 → Lambda silver-to-gold
resource "aws_s3_bucket_notification" "silver_trigger" {
  bucket = aws_s3_bucket.silver.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.silver_to_gold.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "silver/stories_silver_"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_silver_invoke]
}
