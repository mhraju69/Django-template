from rest_framework.permissions import BasePermission


class IsParent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "parent")


class IsChild(BasePermission):
    def has_permission(self, request, view,obj):
        return bool(request.user and request.user.is_authenticated and request.user.role == "child")


class IsEventAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "parent")
    def has_object_permission(self, request, view, obj):
        return obj.admin == request.user


class IsGroupAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "parent")
    def has_object_permission(self, request, view, obj):
        return obj.admin == request.user


class IsChatMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    def has_object_permission(self, request, view, obj):
        return request.user in obj.members.all()
