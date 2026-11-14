import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LocalScriptsTests(unittest.TestCase):
    def preparar(self, pasta, com_kubeconfig=True):
        raiz = Path(pasta) / "repositorio com espacos"
        scripts = raiz / "scripts"
        scripts.mkdir(parents=True)
        for nome in ("kubectl-local.sh", "cluster.sh"):
            shutil.copyfile(ROOT / "scripts" / nome, scripts / nome)
        runtime = Path(pasta) / "dados fora do checkout"
        runtime.mkdir()
        if com_kubeconfig:
            (runtime / "kubeconfig").write_text("configuracao ficticia de teste\n")
        binario = raiz / "bin"
        binario.mkdir()
        for nome in ("kubectl", "terraform"):
            fake = binario / nome
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            fake.chmod(0o700)
        env = dict(os.environ, PATH=str(binario) + os.pathsep + os.environ["PATH"],
                   OFICINA_HOME=str(runtime))
        return raiz, runtime, scripts, env

    def executar(self, scripts, env, nome, *args):
        return subprocess.run(["bash", str(scripts / nome), *args], env=env,
                              capture_output=True, text=True)

    def test_kubectl_usa_config_externo_e_contexto_explicito(self):
        with tempfile.TemporaryDirectory() as pasta:
            _, runtime, scripts, env = self.preparar(pasta)
            resultado = self.executar(scripts, env, "kubectl-local.sh", "get", "nodes")
            self.assertEqual(0, resultado.returncode, resultado.stderr)
            self.assertEqual([f"--kubeconfig={runtime}/kubeconfig", "--context=kind-oficina-fase4",
                              "get", "nodes"], resultado.stdout.splitlines())

    def test_sem_config_nao_usa_contexto_global(self):
        with tempfile.TemporaryDirectory() as pasta:
            _, _, scripts, env = self.preparar(pasta, False)
            resultado = self.executar(scripts, env, "kubectl-local.sh", "get", "nodes")
            self.assertEqual(1, resultado.returncode)
            self.assertEqual("", resultado.stdout)
            self.assertIn("Kubeconfig da Fase 4 nao encontrado", resultado.stderr)

    def test_bloqueia_redirecionamento_de_cluster(self):
        with tempfile.TemporaryDirectory() as pasta:
            _, _, scripts, env = self.preparar(pasta)
            for args in (["--context", "outro"], ["--context=outro"],
                         ["--kubeconfig", "/outro"], ["--kubeconfig=/outro"]):
                with self.subTest(args=args):
                    resultado = self.executar(scripts, env, "kubectl-local.sh", *args)
                    self.assertEqual(2, resultado.returncode)
                    self.assertEqual("", resultado.stdout)

    def test_init_usa_state_persistente_fora_do_checkout(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz, runtime, scripts, env = self.preparar(pasta)
            resultado = self.executar(scripts, env, "cluster.sh", "init", "-input=false")
            self.assertEqual(0, resultado.returncode, resultado.stderr)
            self.assertEqual([f"-chdir={raiz}/cluster", "init",
                              f"-backend-config=path={runtime}/terraform/cluster.tfstate",
                              "-input=false"], resultado.stdout.splitlines())

    def test_comando_invalido_nao_chama_terraform(self):
        with tempfile.TemporaryDirectory() as pasta:
            _, _, scripts, env = self.preparar(pasta)
            resultado = self.executar(scripts, env, "cluster.sh", "import")
            self.assertEqual(2, resultado.returncode)
            self.assertEqual("", resultado.stdout)

    def test_rejeita_runtime_relativo(self):
        with tempfile.TemporaryDirectory() as pasta:
            _, _, scripts, env = self.preparar(pasta)
            env["OFICINA_HOME"] = "pasta-relativa"
            for nome, args in (("cluster.sh", ["plan"]), ("kubectl-local.sh", ["get", "nodes"])):
                with self.subTest(nome=nome):
                    resultado = self.executar(scripts, env, nome, *args)
                    self.assertEqual(2, resultado.returncode)
                    self.assertEqual("", resultado.stdout)


if __name__ == "__main__":
    unittest.main()
