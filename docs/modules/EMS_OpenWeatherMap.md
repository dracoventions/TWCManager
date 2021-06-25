# OpenWeatherMap

## Introduction

The OpenWeatherMap EMS module allows owners to track the relative expected solar generation of their location against weather data obtained from the OpenWeatherMap API.

This allows for owners who don't have the ability to query their inverter generation details to estimate the generator output based on the weather data.

### API Key

Use of the OpenWeatherMap API requires an API Key

### Constructing the Data Array

In order to determine the output relative to the size of the system, historical data is required in order to understand the maximum rate of generation across each month of the year.

The array ```PeakKW``` specified in the configuration for this module contains 12 values, one per month, which represents the peak output value for an entire day on the highest output day of that month.

For example, if the 15th of March was the peak generation day for March (no clouds, peak conditions) and the highest generation value for that day was 13kW at 12PM, you would place the value 13 in the fourth element of the ```PeakKW``` array.

