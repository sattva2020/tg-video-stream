import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardBody, CardHeader, Chip } from '@heroui/react';

export const UserDashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-6 p-4">
      <Card>
        <CardHeader className="flex flex-col items-start px-6 pt-6 pb-0">
          <h2 className="text-xl font-semibold">Welcome, {user?.full_name || user?.email}!</h2>
          <p className="text-default-500 mt-1">
            You are logged in as a standard user.
          </p>
        </CardHeader>
        <CardBody className="px-6 pb-6">
          {/* Additional welcome content could go here */}
        </CardBody>
      </Card>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="px-6 pt-6 pb-0">
            <h3 className="text-lg font-medium">My Profile</h3>
          </CardHeader>
          <CardBody className="px-6 pb-6">
            <div className="space-y-4 text-sm">
              <div className="flex justify-between items-center border-b border-default-100 pb-2">
                <span className="text-default-500">Email</span>
                <span className="font-medium">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-default-500">Status</span>
                <Chip color="success" variant="flat" size="sm">
                  Active
                </Chip>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};
