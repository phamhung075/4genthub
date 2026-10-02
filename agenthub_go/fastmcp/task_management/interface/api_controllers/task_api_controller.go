// Package api_controllers re-exports the modular TaskAPIController.
package api_controllers

import (
	taskapicontroller "agenthub/fastmcp/task_management/interface/api_controllers/task_api_controller"
)

// TaskAPIController re-exports the modular TaskAPIController.
type TaskAPIController = taskapicontroller.TaskAPIController

// NewTaskAPIController re-exports the constructor.
var NewTaskAPIController = taskapicontroller.NewTaskAPIController
