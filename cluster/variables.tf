variable "runtime_dir" {
  description = "Diretorio privado e persistente, fora do checkout do runner."
  type        = string
  default     = "~/.local/share/oficina-fase4"

  validation {
    condition     = startswith(var.runtime_dir, "/") || startswith(var.runtime_dir, "~/")
    error_message = "Use um caminho absoluto ou iniciado por ~/."
  }
}
