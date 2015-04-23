# -*- coding: utf-8 -*-

import pytest
import sys
import time
from test_base_class import TestBaseClass

aerospike = pytest.importorskip("aerospike")


class TestCreateUser(TestBaseClass):

    pytestmark = pytest.mark.skipif(
        TestBaseClass().get_hosts()[1] == None,
        reason="No user specified, may be not secured cluster.")

    def setup_method(self, method):
        """
        Setup method
        """
        hostlist, user, password = TestBaseClass().get_hosts()
        config = {"hosts": hostlist}

        self.client = aerospike.client(config).connect(user, password)

        self.delete_users = []

    def teardown_method(self, method):
        """
        Teardown method
        """

        policy = {}

        for user in self.delete_users:
            self.client.admin_drop_user(policy, user)

        self.client.close()

    def test_create_user_without_any_parameters(self):

        with pytest.raises(TypeError) as typeError:
            self.client.admin_create_user()

        assert "Required argument 'policy' (pos 1) not found" in typeError.value

    def test_create_user_with_proper_parameters(self):

        policy = {"timeout": 1000}
        user = "user1"
        password = "user1"
        roles = ["read", "read-write", "sys-admin"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        time.sleep(2)

        assert status == 0

        user_details = self.client.admin_query_user(policy, user)

        assert user_details == [{
            'roles': ['sys-admin',
                      'read',
                      'read-write', ],
            'roles_size': 3,
            'user': 'user1'
        }]

        self.delete_users.append('user1')

    def test_create_user_with_invalid_timeout_policy_value(self):

        policy = {"timeout": 0.1}
        user = "user3"
        password = "user3"
        roles = ['sys-admin']

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == -2
        assert exception.value[1] == "timeout is invalid"

    def test_create_user_with_proper_timeout_policy_value(self):

        policy = {'timeout': 5}
        user = "user2"
        password = "user2"
        roles = ["read-write", "sys-admin"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        time.sleep(2)

        assert status == 0

        user_details = self.client.admin_query_user({}, user)

        assert user_details[0]['user'] == "user2"

        assert user_details[0]['roles'].sort() == roles.sort()

        self.delete_users.append('user2')

    def test_create_user_with_none_username(self):

        policy = {'timeout': 0}
        user = None
        password = "user3"
        roles = ["sys-admin"]

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == -2
        assert exception.value[1] == "Username should be a string"

    def test_create_user_with_empty_username(self):

        policy = {}
        user = ""
        password = "user3"
        roles = ["read-write"]

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == 60
        assert exception.value[1] == "AEROSPIKE_INVALID_USER"

    def test_create_user_with_special_characters_in_username(self):

        policy = {}
        user = "!#Q#AEQ@#$%&^*((^&*~~~````"
        password = "user4"
        roles = ["read-write"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        assert status == 0

        self.delete_users.append(user)

    def test_create_user_with_none_password(self):

        policy = {}
        user = "user4"
        password = None
        roles = ["sys-admin"]

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == -2
        assert exception.value[1] == "Password should be a string"

    def test_create_user_with_empty_string_as_password(self):

        policy = {}
        user = "user5"
        password = ""
        roles = ["read-write"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        assert status == 0
        time.sleep(2)
        self.delete_users.append(user)

    def test_create_user_with_special_characters_in_password(self):

        policy = {}
        user = "user6"
        password = "@#!$#$WERWE%&%$"
        roles = ["sys-admin"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        assert status == 0

        self.delete_users.append(user)

    def test_create_user_with_too_long_username(self):

        policy = {}
        user = "user$" * 1000
        password = "user10"
        roles = ["sys-admin"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == 60
        assert exception.value[1] == "AEROSPIKE_INVALID_USER"

    def test_create_user_with_too_long_password(self):

        policy = {'timeout': 1000}
        user = "user10"
        password = "user#" * 1000
        roles = ["read-write"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        assert status == 0
        time.sleep(1)

        user_details = self.client.admin_query_user(policy, user)

        assert user_details == [
            {'roles': ['read-write'],
             'roles_size': 1,
             'user': 'user10'}
        ]

        self.delete_users.append(user)

    def test_create_user_with_empty_roles_list(self):

        policy = {}
        user = "user7"
        password = "user7"
        roles = []

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == 70
        assert exception.value[1] == "AEROSPIKE_INVALID_ROLE"

    def test_create_user_with_invalid_role(self):

        policy = {}
        user = "user12"
        password = "user12"
        roles = ["viewer"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, len(roles))

        assert exception.value[0] == 70
        assert exception.value[1] == "AEROSPIKE_INVALID_ROLE"

    def test_create_user_with_different_roles_and_roles_size(self):

        policy = {}
        user = "user11"
        password = "user11"
        roles = ["read-write"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        with pytest.raises(Exception) as exception:
            status = self.client.admin_create_user(policy, user, password,
                                                   roles, 2)

        assert exception.value[0] == 70
        assert exception.value[1] == "AEROSPIKE_INVALID_ROLE"

    def test_create_user_with_non_user_admin_user(self):

        policy = {}
        user = "non_admin"
        password = "non_admin"
        roles = ["read-write"]

        try:
            self.client.admin_drop_user(policy, user)
        except:
            pass

        status = self.client.admin_create_user(policy, user, password, roles,
                                               len(roles))

        assert status == 0

        config = {"hosts": TestCreateUser.hostlist}

        non_admin_client = None

        with pytest.raises(Exception) as exception:
            non_admin_client = aerospike.client(config).connect("non_admin",
                                                                "non_admin")
            status = non_admin_client.admin_create_user(
                policy, "user78", password, roles, len(roles))

        if non_admin_client:
            non_admin_client.close()

        assert exception.value[0] == 81

        self.delete_users.append("non_admin")
