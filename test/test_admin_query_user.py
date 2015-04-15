
# -*- coding: utf-8 -*-

import pytest
import sys
import time
from test_base_class import TestBaseClass

try:
    import aerospike
    from aerospike.exception import *
except:
    print "Please install aerospike python client."
    sys.exit(1)

class TestQueryUser(TestBaseClass):

    def setup_method(self, method):

        """
        Setup method
        """
        hostlist, user, password = TestBaseClass().get_hosts()
        config = {
                "hosts": hostlist
                }
        self.client = aerospike.client(config).connect( user, password )

        policy = {}
        user = "example"
        password = "foo2"
        roles = ["read-write", "sys-admin", "read"]

        status = self.client.admin_create_user( policy, user, password, roles, len(roles) )

        self.delete_users = []

    def teardown_method(self, method):

        """
        Teardown method
        """

        policy = {}

        self.client.admin_drop_user( policy, "example" )

        self.client.close()

    def test_query_user_without_any_parameters(self):

        with pytest.raises(TypeError) as typeError:
            self.client.admin_query_user()

        assert "Required argument 'policy' (pos 1) not found" in typeError.value

    def test_query_user_with_proper_parameters(self):

        policy = {}
        user = "example"

        time.sleep(2)
        user_details = self.client.admin_query_user( policy, user )

        assert user_details == [{'roles': ['read', 'read-write', 'sys-admin'], 'roles_size':
3, 'user': user}]

    def test_query_user_with_invalid_timeout_policy_value(self):

        policy = { "timeout" : 0.1 }
        user = "example"

        try:
            status = self.client.admin_query_user( policy, user )

        except ParamError as exception:
            assert exception.code == -2
            assert exception.msg == "timeout is invalid"

    def test_query_user_with_proper_timeout_policy_value(self):

        policy = { 'timeout' : 5 }
        user = "example"

        time.sleep(2)
        user_details = self.client.admin_query_user( policy, user )

        assert user_details == [{'roles': ['read','read-write','sys-admin'],
'roles_size': 3, 'user': user}]

    def test_query_user_with_none_username(self):

        policy = { 'timeout' : 0 }
        user = None

        try:
            user_details = self.client.admin_query_user( policy, user )

        except ParamError as exception:
            assert exception.code == -2
            assert exception.msg == "Username should be a string"

    def test_query_user_with_empty_username(self):

        policy = {}
        user = ""

        try:
            status = self.client.admin_query_user( policy, user )

        except InvalidUser as exception:
            assert exception.code == 60
            assert exception.msg == "AEROSPIKE_INVALID_USER"

    def test_query_user_with_nonexistent_username(self):

        policy = {}
        user = "non-existent"

        try:
            status = self.client.admin_query_user( policy, user )

        except InvalidUser as exception:
            assert exception.code == 60
            assert exception.msg == "AEROSPIKE_INVALID_USER"

    def test_query_user_with_no_roles(self):

        policy = {}
        user = "example"
        roles = ["sys-admin", "read", "read-write"]

        status = self.client.admin_revoke_roles(policy, user, roles, len(roles))
        assert status == 0
        time.sleep(2)

        user_details = self.client.admin_query_user( policy, user )

        assert user_details == [{'roles': [], 'roles_size':
0, 'user': 'example'}]

    def test_query_user_with_extra_argument(self):

        """
            Invoke query_user() with extra argument.
        """
        policy = {
            'timeout': 1000
        }
        with pytest.raises(TypeError) as typeError:
            self.client.admin_query_user( policy, "foo", "" )

        assert "admin_query_user() takes at most 2 arguments (3 given)" in typeError.value

    def test_query_user_with_policy_as_string(self):

        """
            Invoke query_user() with policy as string
        """
        policy = ""
        try:
            self.client.admin_query_user( policy, "foo")

        except AerospikeError as exception:
            assert exception.code == -2L
            assert exception.msg == "policy must be a dict"
