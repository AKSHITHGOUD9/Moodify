export default function ProfileDropdown({ user, onClose, onLogout }) {
  return (
    <div className="profile-dropdown-overlay" onClick={onClose}>
      <div className="profile-dropdown" onClick={(e) => e.stopPropagation()}>
        <div className="profile-header">
          <h3>Profile</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="profile-info">
          <p><strong>Name:</strong> {user?.display_name}</p>
          <p><strong>Email:</strong> {user?.email}</p>
          <p><strong>Country:</strong> {user?.country}</p>
          <p><strong>Followers:</strong> {user?.followers}</p>
        </div>
        
        <div className="profile-actions">
          <button className="logout-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}
