import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from new_relic_config import read_new_relic


class ObservabilityTests(unittest.TestCase):
    def test_chart_usa_secret_e_nao_recebe_key_nos_values(self):
        values = yaml.safe_load((ROOT / "observability/values.yaml").read_text())
        self.assertEqual("oficina-fase4", values["global"]["cluster"])
        self.assertEqual("newrelic-license", values["global"]["customSecretName"])
        self.assertTrue(values["global"]["lowDataMode"])
        self.assertNotIn("licenseKey", values["global"])

    def test_evitar_duplicar_logs_e_componentes_desnecessarios(self):
        values = yaml.safe_load((ROOT / "observability/values.yaml").read_text())
        for chart in ("newrelic-logging", "nri-metadata-injection", "nr-ebpf-agent", "newrelic-prometheus-agent"):
            self.assertFalse(values[chart]["enabled"])
        self.assertTrue(values["newrelic-infrastructure"]["enabled"])
        self.assertTrue(values["kube-state-metrics"]["enabled"])
        self.assertNotIn("secrets", values["kube-state-metrics"]["collectors"])

    def test_agentes_tem_limites_compativeis_com_laboratorio(self):
        values = yaml.safe_load((ROOT / "observability/values.yaml").read_text())
        infra = values["newrelic-infrastructure"]
        self.assertFalse(infra["controlPlane"]["enabled"])
        self.assertTrue(infra["rbac"]["kubeletFineGrainedAuth"])
        self.assertEqual("256Mi", infra["kubelet"]["agent"]["resources"]["limits"]["memory"])
        self.assertEqual("128Mi", values["kube-state-metrics"]["resources"]["limits"]["memory"])

    def test_configuracao_e_opcional_e_validada(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertFalse(read_new_relic(home)["enabled"])
            path = home / "secrets/newrelic.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"enabled": True, "license_key": "chave-ficticia-somente-teste"}))
            self.assertTrue(read_new_relic(home)["enabled"])
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            path.write_text(json.dumps({"enabled": True, "license_key": ""}))
            with self.assertRaises(ValueError):
                read_new_relic(home)

    def test_state_e_configuracao_privados_fora_do_checkout(self):
        script = (ROOT / "scripts/deploy_observability.py").read_text()
        self.assertIn('read_new_relic(home)', script)
        self.assertIn('"observability", settings', script)
        self.assertNotIn("print(settings)", script)
        terraform = (ROOT / "observability/versions.tf").read_text()
        self.assertIn('config_context = "kind-oficina-fase4"', terraform)
        self.assertIn("sensitive = true", terraform)


if __name__ == "__main__":
    unittest.main()
