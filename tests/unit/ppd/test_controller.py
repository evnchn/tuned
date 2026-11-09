import os
import tempfile
import unittest
from unittest import mock

import tuned.ppd.controller as ppd_controller
from tuned.ppd.config import ProfileMap, PPD_BALANCED, PPD_PERFORMANCE, PPD_POWER_SAVER

PROFILES = {PPD_POWER_SAVER: "powersave", PPD_BALANCED: "balanced", PPD_PERFORMANCE: "throughput-performance"}


class BaseProfileTestCase(unittest.TestCase):
	def setUp(self):
		fd, self._base_profile_file = tempfile.mkstemp()
		os.close(fd)
		self.addCleanup(os.remove, self._base_profile_file)
		config = mock.Mock(default_profile=PPD_BALANCED)
		config.ppd_to_tuned = ProfileMap(PROFILES, PROFILES)
		config.tuned_to_ppd = ProfileMap({v: k for k, v in PROFILES.items()}, {v: k for k, v in PROFILES.items()})
		self._tuned = mock.Mock()
		self._tuned.recommend_profile.return_value = "unknown-tuned-profile"
		self._tuned.switch_profile.return_value = (True, "")
		for target, value in [
			("PPD_BASE_PROFILE_FILE", self._base_profile_file),
			("PPDConfig", mock.Mock(return_value=config)),
			("pyinotify", mock.Mock()),
		]:
			patcher = mock.patch.object(ppd_controller, target, value)
			patcher.start()
			self.addCleanup(patcher.stop)
		for method in ["_setup_battery_signaling", "_setup_inotify"]:
			patcher = mock.patch.object(ppd_controller.Controller, method)
			patcher.start()
			self.addCleanup(patcher.stop)

	def _start(self, saved):
		with open(self._base_profile_file, "w") as f:
			f.write(saved)
		ppd_controller.Controller(mock.Mock(), self._tuned)
		with open(self._base_profile_file) as f:
			return f.read()

	def test_valid_base_profile_is_restored(self):
		self.assertEqual(self._start(PPD_PERFORMANCE + "\n"), PPD_PERFORMANCE + "\n")
		self._tuned.switch_profile.assert_called_with("throughput-performance")

	def test_corrupted_base_profile_falls_back_to_default(self):
		self.assertEqual(self._start("\0" * 12), PPD_BALANCED + "\n")
		self._tuned.switch_profile.assert_called_with("balanced")

	def test_stale_base_profile_falls_back_to_default(self):
		self.assertEqual(self._start("alienware-balanced\n"), PPD_BALANCED + "\n")
