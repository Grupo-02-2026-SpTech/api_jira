variable "aws_region" {
  description = "Região AWS onde os recursos serão criados"
  type        = string
  default     = "us-east-1"
}

variable "lab_role_arn" {
  description = "ARN da role LabRole da conta AWS Academy. Formato: arn:aws:iam::ACCOUNT_ID:role/LabRole"
  type        = string
}

variable "pandas_layer_arn" {
  description = "ARN do layer AWSSDKPandas compatível com o runtime escolhido"
  type        = string
  # ARN padrão para AWSSDKPandas-Python314 em us-east-1 (confirme no console AWS → Lambda → Layers)
  default     = "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python314:2"
}

variable "python_runtime" {
  description = "Runtime Python da Lambda (deve ser compatível com o layer adicionado)"
  type        = string
  default     = "python3.12"
}
