import sys
import tempfile
import unittest
from pathlib import Path
from string import Template

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from local_runtime import private_json, operation_lock


class PlatformTests(unittest.TestCase):
    def test_mensageria_tem_volume_probes_e_limites(self):
        text = Template((ROOT / "k8s/elasticmq-statefulset.yaml.tftpl").read_text()).substitute(config_checksum="a" * 64)
        stateful = yaml.safe_load(text)
        self.assertEqual("oficina-plataforma", stateful["metadata"]["namespace"])
        pod = stateful["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        container = pod["containers"][0]
        self.assertIn("resources", container)
        self.assertIn("readinessProbe", container)
        self.assertIn("livenessProbe", container)
        self.assertIn({"name": "data", "persistentVolumeClaim": {"claimName": "elasticmq-data"}}, pod["volumes"])

    def test_mensageria_so_usa_service_interno(self):
        service = yaml.safe_load((ROOT / "k8s/elasticmq-service.yaml").read_text())
        self.assertEqual("ClusterIP", service["spec"]["type"])

    def test_persistencia_de_filas_e_mensagens_configurada(self):
        config = (ROOT / "k8s/elasticmq.conf").read_text()
        for setting in ('messages-storage.enabled = true', 'messages-storage.uri = "jdbc:h2:/data/elasticmq-h2"',
                        'queues-storage.enabled = true', 'queues-storage.path = "/data/queues.conf"'):
            self.assertIn(setting, config)
        for queue in ("cobranca-comandos", "execucao-comandos", "ordens-eventos"):
            self.assertIn(queue + "-dlq", config)

    def test_senha_ausente_nao_e_trocada_sobre_recurso_existente(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            private_json(Path(folder) / "secrets.json", lambda: {}, existing_resources=True)

    def test_operacao_exclusiva_libera_apos_falha(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with self.assertRaises(ValueError):
                with operation_lock(home):
                    raise ValueError("falha simulada")
            with operation_lock(home, timeout=0):
                pass


if __name__ == "__main__":
    unittest.main()
