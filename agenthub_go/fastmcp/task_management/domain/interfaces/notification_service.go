package interfaces

import "context"

// NotificationType is the notification channel enumeration.
type NotificationType string

const (
	NotificationTypeEmail    NotificationType = "email"
	NotificationTypeWebhook  NotificationType = "webhook"
	NotificationTypeInternal NotificationType = "internal"
	NotificationTypePush     NotificationType = "push"
)

// NotificationTypeValues lists the types in declaration order.
var NotificationTypeValues = []NotificationType{NotificationTypeEmail, NotificationTypeWebhook, NotificationTypeInternal, NotificationTypePush}

// INotification is a notification (Python properties become methods).
type INotification interface {
	NotificationType() NotificationType
	Recipient() string
	Message() string
	Metadata() map[string]any
}

// INotificationService sends and schedules notifications.
type INotificationService interface {
	SendNotification(ctx context.Context, notification INotification) (bool, error)
	SendBulkNotifications(ctx context.Context, notifications []INotification) ([]bool, error)
	ScheduleNotification(ctx context.Context, notification INotification, delaySeconds int) (string, error)
	CancelNotification(ctx context.Context, notificationID string) (bool, error)
	CreateNotification(notificationType NotificationType, recipient, message string, metadata map[string]any) INotification
}
