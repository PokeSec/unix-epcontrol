/*
 * main.cpp : Unix entry point
 *
 * This file is part of EPControl.
 *
 * Copyright (C) 2016  Jean-Baptiste Galet & Timothe Aeberhardt
 *
 * EPControl is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * EPControl is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with EPControl.  If not, see <http://www.gnu.org/licenses/>.
 */
#include <string>
#include <vector>
#include <string.h>
#include <limits.h>
#include <stdlib.h>
#include <unistd.h>

#include "Python.h"

int main(int argc, char *argv[])
{
    // Retrieve normalized executable path and chdir to it
    std::string exe_path;
    std::string exe = argv[0];

    exe_path = exe.substr(0, exe.rfind('/'));

    if (exe[0] != '/')
    {
        char current_dir_name[PATH_MAX];
        char* res = getcwd(current_dir_name, PATH_MAX);
        if (res == NULL)
            return 1;
        exe_path = std::string(current_dir_name) + '/' + exe_path + '/';
    }

    char normalized_exe_path[PATH_MAX];
    realpath(exe_path.c_str(), normalized_exe_path);
    chdir(normalized_exe_path);

    // Prepare arguments for call
    wchar_t **wargs = (wchar_t **)malloc((argc) * sizeof(wchar_t *));
    if (!wargs)
        return 1;

    for( int i = 0 ; i < argc ; ++i )
    {
        wargs[i] = Py_DecodeLocale(argv[i], NULL);
    }

    int ret = -1;
    // Call Python
    wchar_t pyHome[] = L"lib/pylib";
    Py_SetPythonHome(pyHome);
    Py_SetPath(L"lib/pytool:lib/pylib:lib/pylib/lib-dynload:lib/agentlib:lib/pylib/site-packages");
    if (argc > 1 && strcmp(argv[1], "-c") == 0)
    {
        ret = Py_Main(argc, wargs);
    }
	// Handle other command lines switches
	else if (argc >= 2)
	{
		// Start Python engine
	    Py_Initialize();
		PySys_SetArgv(argc, wargs);

		PyObject *cmd_mod, *cmd_dict, *run_meth, *result;
		cmd_mod = PyImport_ImportModule("epc.unix.command_services");
		if (cmd_mod)
		{
			cmd_dict = PyModule_GetDict(cmd_mod);
			if (cmd_dict)
			{
				run_meth = PyDict_GetItemString(cmd_dict, "run");
				if (run_meth && PyCallable_Check(run_meth))
				{
					result = PyObject_CallObject(run_meth, NULL);
					if (result && PyLong_Check(result))
					{
						ret = PyLong_AsLong(result);
						Py_DECREF(result);
					}
					Py_DECREF(run_meth);
				}
				Py_DECREF(cmd_dict);
			}
			Py_DECREF(cmd_mod);
		}
		Py_Finalize();
	}
    else 
    {
    	// Start Python engine
	    Py_Initialize();
		PySys_SetArgv(argc, wargs);

		PyObject *service, *service_dict, *main_meth, *result;
		service = PyImport_ImportModule("epc.unix.service");
		if (service)
		{
			service_dict = PyModule_GetDict(service);
			if (service_dict)
			{
				main_meth = PyDict_GetItemString(service_dict, "main");
				if (main_meth && PyCallable_Check(main_meth))
				{
					result = PyObject_CallObject(main_meth, NULL);
					if (result && PyLong_Check(result))
					{
						ret = PyLong_AsLong(result);
						Py_DECREF(result);
					}
					Py_DECREF(main_meth);
				}
				Py_DECREF(service_dict);
			}
			Py_DECREF(service);
		}
		Py_Finalize();
    }
    free(wargs);
    return ret;
}
