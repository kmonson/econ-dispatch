# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

# Copyright (c) 2017, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation
# are those of the authors and should not be interpreted as representing
# official policies, either expressed or implied, of the FreeBSD
# Project.
#
# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization that
# has cooperated in the development of these materials, makes any
# warranty, express or implied, or assumes any legal liability or
# responsibility for the accuracy, completeness, or usefulness or any
# information, apparatus, product, software, or process disclosed, or
# represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does not
# necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830
# }}}

import logging
_log = logging.getLogger(__name__)

import networkx as nx

from pprint import pprint

class SystemModel(object):
    def __init__(self, optimizer, weather_model, optimizer_debug_csv=None):
        self.component_graph = nx.MultiDiGraph()
        self.instance_map = {}

        self.forecast_models = {}

        self.optimizer = optimizer
        self.weather_model = weather_model

        self.optimizer_debug_csv = optimizer_debug_csv

    def add_forecast_model(self, model, name):
        self.forecast_models[name] = model

    def add_component(self, component, type_name):
        self.component_graph.add_node(component.name, type = type_name)

        if component.name in self.instance_map:
            _log.warning("Duplicate component names: " + component.name)

        self.instance_map[component.name] = component

    def add_connection(self, output_component_name, input_component_name, io_type=None):
        try:
            output_component = self.instance_map[output_component_name]
        except KeyError:
            _log.error("No component named {}".format(output_component_name))
            raise

        try:
            input_component = self.instance_map[input_component_name]
        except KeyError:
            _log.error("No component named {}".format(input_component_name))
            raise


        output_types = output_component.get_output_metadata()
        input_types = input_component.get_input_metadata()

        _log.debug("Output types: {}".format(output_types))
        _log.debug("Input types: {}".format(input_types))

        real_io_types = []
        if io_type is not None:
            real_io_types = [io_type]
        else:
            real_io_types = [x for x in output_types if x in input_types]

        for real_io_type in real_io_types:
            _log.debug("Adding connection for io type: "+real_io_type)
            self.component_graph.add_edge(output_component.name, input_component.name, label=real_io_type)

        return len(real_io_types)

    def get_forecasts(self, now):
        weather_forecasts = self.weather_model.get_weather_forecast(now)
        #Loads were updated previously when we updated all components
        forecasts = []

        for weather_forecast in weather_forecasts:
            timestamp = weather_forecast.pop("timestamp")
            record = {}
            for name, model in self.forecast_models.iteritems():
                record.update(model.derive_variables(timestamp, weather_forecast))

            forecasts.append(record)

        return forecasts


    def update_components(self, now, inputs):
        _log.debug("Updating Components")
        for component in self.instance_map.itervalues():
            component.update_parameters(timestamp=now, **inputs)

    def run_general_optimizer(self, now, predicted_loads, parameters):
        _log.debug("Running General Optimizer")
        results = self.optimizer(now, predicted_loads, parameters)

        if self.optimizer_debug_csv is not None:
            self.optimizer_debug_csv.writerow(results, predicted_loads, now)

        return results

    def get_parameters(self, now, inputs):
        self.update_components(now, inputs)

        results = {}
        for component in self.instance_map.itervalues():
            parameters = component.get_optimization_parameters()
            results.update(parameters)

        return results

    def run_component_optimizer(self, component_loads):
        _log.debug("Running Component Optimizer")

    def get_commands(self):
        return {}

    def run(self, now, inputs):
        _log.info("Running " + str(now))
        forecasts = self.get_forecasts(now)
        parameters = self.get_parameters(now, inputs)
        component_loads = self.run_general_optimizer(now, forecasts, parameters)
        self.run_component_optimizer(component_loads)
        commands = self.get_commands()

        return commands






