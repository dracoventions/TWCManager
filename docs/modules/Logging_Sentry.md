# Sentry

## Introduction

Sentry is an open-source SaaS full-stack error tracking system.

Using sentry, applications can be profiled and monitored for errors across releases, with a user-friendly web based interface to track and manage errors.

## Installation

Note: Using Sentry requires a minimum Python version of 3.4.

All dependencies and prerequisites for using Sentry are installed automatically as part of the ```setup.py``` script.

## Step by Step Setup

   1 Sign up to https://sentry.io

   2 Create a project for HomeAssistant

   3 Select Python as the platform

   4 Give the project a name

   5 From the Configure Python screen, copy the URL specified in the sentry_sdk.init funciton, and paste it into the DSN configuration field in ```config.yaml```
