# -*- coding: utf-8 -*-

import pytest
import sys
from .test_base_class import TestBaseClass
from aerospike import exception as e

aerospike = pytest.importorskip("aerospike")
try:
    import aerospike
except:
    print("Please install aerospike python client.")
    sys.exit(1)

class TestLog(object):

    def test_set_log_level_correct(self):
        """
        Test log level with correct parameters
        """

        response = aerospike.set_log_level(aerospike.LOG_LEVEL_DEBUG)

        assert response == 0

    def test_set_log_handler_correct(self):
        """
        Test log handler with correct parameters
        """

        response = aerospike.set_log_level(aerospike.LOG_LEVEL_DEBUG)
        aerospike.enable_log_handler()

        hostlist, user, password = TestBaseClass.get_hosts()
        config = {
            "hosts": hostlist
        }
        if user is None and password is None:
            client = aerospike.client(config).connect()
        else:
            client = aerospike.client(config).connect(user, password)

        assert response == 0
        client.close()

    def test_set_log_level_None(self):
        """
        Test log level with log level as None
        """
        try:
            aerospike.set_log_level(None)

        except e.ParamError as exception:
            assert exception.code == -2
            assert exception.msg == 'Invalid log level'

    def test_set_log_level_incorrect(self):
        """
        Test log level with log level incorrect
        """
        response = aerospike.set_log_level(9)

        assert response == 0

    def test_set_log_handler_extra_parameter(self):
        """
        Test log handler with extra parameter
        """

        aerospike.set_log_level(aerospike.LOG_LEVEL_DEBUG)

        with pytest.raises(TypeError) as typeError:
            aerospike.enable_log_handler()

        assert "setLogHandler() takes at most 1 argument (2 given)" in str(
            typeError.value)
