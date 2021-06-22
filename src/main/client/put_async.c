/*******************************************************************************
 * Copyright 2013-2021 Aerospike, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ******************************************************************************/

#include <Python.h>
#include <stdbool.h>

#include <aerospike/aerospike_key.h>
#include <aerospike/as_key.h>
#include <aerospike/as_error.h>
#include <aerospike/as_record.h>

#include "client.h"
#include "conversions.h"
#include "exceptions.h"
#include "policy.h"

// Struct for Python User-Data for the Callback
typedef struct {
	as_key key;
	as_error error;
	PyObject *callback;
	AerospikeClient *client;
} LocalData;

LocalData* put_async_cb_create(void)
{
	return cf_malloc(sizeof(LocalData));
}

void put_async_cb_destroy(LocalData *uData)
{
	cf_free(uData);
}

void 
write_async_callback(as_error* error, void* udata, as_event_loop* event_loop)
{
	PyObject *py_key = NULL;
	PyObject *py_return = NULL;
	PyObject *py_arglist = NULL;

	// Extract callback user-data
	LocalData *data = (LocalData *)udata;
	as_error *err = &data->error;
	PyObject *py_callback = data->callback;

	// Lock Python State
	PyGILState_STATE gstate;
	gstate = PyGILState_Ensure();

	// Convert as_key to python key object
	key_to_pyobject(err, &data->key, &py_key);

	if (error) {

		PyObject *py_err = NULL;
		error_to_pyobject(error, &py_err);
		PyObject *exception_type = raise_exception(err);
		if (PyObject_HasAttrString(exception_type, "key")) {
			PyObject_SetAttrString(exception_type, "key", py_key);
		}
		if (PyObject_HasAttrString(exception_type, "bin")) {
			PyObject_SetAttrString(exception_type, "bin", Py_None);
		}
		PyErr_SetObject(exception_type, py_err);
		Py_DECREF(py_err);
		goto CLEANUP;
	}

	// Build Python Function Arguments
	py_arglist = PyTuple_New(1);
	PyTuple_SetItem(py_arglist, 0, py_key);

	// Invoke Python Callback
	py_return = PyObject_Call(py_callback, py_arglist, NULL);

	// Release Python Function Arguments
	Py_DECREF(py_arglist);

	// handle return value
	if (!py_return) {
		// an exception was raised, handle it (someday)
		// for now, we bail from the loop
		as_error_update(err, AEROSPIKE_ERR_CLIENT,
						"read_async_callback function raised an exception");
	}
	else {
		Py_DECREF(py_return);
	}


CLEANUP:

	if (udata) {
		as_key_destroy(&data->key);
		//todo: dont free cb data in case of retry logic
		put_async_cb_destroy(udata);
	}

	PyGILState_Release(gstate);

	return;
}

/**
 *******************************************************************************************************
 * Puts a record asynchronously to the Aerospike DB.
 *
 * @param self                  AerospikeClient object
 * @param args                  The args is a tuple object containing an argument
 *                              list passed from Python to a C function
 * @param kwds                  Dictionary of keywords
 *
 * Returns an integer status. 0(Zero) is success value.
 * In case of error,appropriate exceptions will be raised.
 *******************************************************************************************************
 */
PyObject *AerospikeClient_Put_Async(AerospikeClient *self, PyObject *args,
							  PyObject *kwds)
{
		// Aerospike Client Arguments
	as_error err;
	as_policy_write write_policy;
	as_policy_write *write_policy_p = NULL;
	as_record rec;

	// For converting predexp.
	as_exp exp_list;
	as_exp *exp_list_p = NULL;

	// For converting predexp.
	as_predexp_list predexp_list;
	as_predexp_list *predexp_list_p = NULL;

	// Initialisation flags
	bool key_initialised = false;
	bool record_initialised = false;

	// Initialize record
	as_record_init(&rec, 0);
	record_initialised = true;

	as_static_pool static_pool;
	memset(&static_pool, 0, sizeof(static_pool));

	// Python Function Arguments
	PyObject *py_callback = NULL;
	PyObject *py_key = NULL;
	PyObject *py_bins = NULL;
	PyObject *py_meta = NULL;
	PyObject *py_policy = NULL;
	PyObject *py_serializer_option = NULL;
	long serializer_option = SERIALIZER_PYTHON;

	// Python Function Keyword Arguments
	static char *kwlist[] = {"put_callback", "key",	   "bins",		 "meta",
							 "policy", "serializer", NULL};
	// Lock Python State
	// PyGILState_STATE gstate;
	// gstate = PyGILState_Ensure();

	// Python Function Argument Parsing
	if (PyArg_ParseTupleAndKeywords(args, kwds, "OOO|OOO:put_async", kwlist, 
									&py_callback, &py_key,
									&py_bins, &py_meta, &py_policy,
									&py_serializer_option) == false) {
		return NULL;
	}

	// Create and initialize callback user-data
	LocalData *uData = put_async_cb_create();
	uData->callback = py_callback;
	uData->client = self;
	as_error_init(&uData->error);

	as_status status = AEROSPIKE_OK;

	// Initialize error
	as_error_init(&err);

	if (py_serializer_option) {
		if (PyInt_Check(py_serializer_option) ||
			PyLong_Check(py_serializer_option)) {
			self->is_client_put_serializer = true;
			serializer_option = PyLong_AsLong(py_serializer_option);
		}
	}
	else {
		self->is_client_put_serializer = false;
	}

	// Initialize error
	as_error_init(&err);

	if (!self || !self->as) {
		as_error_update(&err, AEROSPIKE_ERR_PARAM, "Invalid aerospike object");
		goto CLEANUP;
	}

	if (!self->is_conn_16) {
		as_error_update(&err, AEROSPIKE_ERR_CLUSTER,
						"No connection to aerospike cluster");
		goto CLEANUP;
	}

	// Convert python key object to as_key
	pyobject_to_key(&err, py_key, &uData->key);
	if (err.code != AEROSPIKE_OK) {
		goto CLEANUP;
	}
	// Key is initialised successfully.
	key_initialised = true;

	// Convert python bins and metadata objects to as_record
	pyobject_to_record(self, &err, py_bins, py_meta, &rec, serializer_option,
					   &static_pool);
	if (err.code != AEROSPIKE_OK) {
		goto CLEANUP;
	}

	// Convert python policy object to as_policy_write
	pyobject_to_policy_write(self, &err, py_policy, &write_policy,
							 &write_policy_p, &self->as->config.policies.write,
							 &predexp_list, &predexp_list_p, &exp_list,
							 &exp_list_p);
	if (err.code != AEROSPIKE_OK) {
		goto CLEANUP;
	}

	// Invoke operation
	Py_BEGIN_ALLOW_THREADS
	status = aerospike_key_put_async(self->as, &uData->error, write_policy_p, 
									&uData->key, &rec, write_async_callback, 
									uData, NULL, NULL);
	Py_END_ALLOW_THREADS
	if (status != AEROSPIKE_OK || err.code != AEROSPIKE_OK) {
		goto CLEANUP;
	}

CLEANUP:
	POOL_DESTROY(&static_pool);

	if (exp_list_p) {
		as_exp_destroy(exp_list_p);
	}

	if (predexp_list_p) {
		as_predexp_list_destroy(&predexp_list);
	}

	if (record_initialised == true) {
		// Destroy the record if it is initialised.
		as_record_destroy(&rec);
	}

	// If an error occurred, tell Python.
	if (err.code != AEROSPIKE_OK) {
		PyObject *py_err = NULL;
		error_to_pyobject(&err, &py_err);
		PyObject *exception_type = raise_exception(&err);
		if (PyObject_HasAttrString(exception_type, "key")) {
			PyObject_SetAttrString(exception_type, "key", py_key);
		}
		if (PyObject_HasAttrString(exception_type, "bin")) {
			PyObject_SetAttrString(exception_type, "bin", py_bins);
		}
		PyErr_SetObject(exception_type, py_err);
		Py_DECREF(py_err);

		if (key_initialised == true) {
			// Destroy the key if it is initialised.
			as_key_destroy(&uData->key);
		}
		if (uData) {
			put_async_cb_destroy(uData);
		}
		return NULL;
	}

	// PyGILState_Release(gstate);

	return PyLong_FromLong(0);
}
