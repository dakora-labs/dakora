"""Email templates for invitation system"""


def render_confirmation_email(user_name: str, user_email: str) -> str:
    """Render confirmation email for invitation request submission"""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Invitation Request Received</title></head>'
        '<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,\'Helvetica Neue\',Arial,sans-serif;background:#f9fafb">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 20px">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;box-shadow:0 4px 6px rgba(0,0,0,0.05);overflow:hidden">'
        '<tr><td style="background:#fff;padding:40px;text-align:center;border-bottom:1px solid #e5e7eb">'
        '<img src="https://playground.dakora.io/logo-light.png" alt="Dakora Studio" style="max-width:200px;height:auto;margin:0 auto;display:block">'
        '</td></tr>'
        '<tr><td style="padding:40px">'
        f'<p style="margin:0 0 24px;color:#4b5563;font-size:16px;line-height:1.6">Hi {user_name},</p>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px;line-height:1.6">We\'ve received your request to join Dakora Studio. Our team is excited to learn more about your use case!</p>'
        '<div style="background:#f9fafb;border-left:4px solid #E7390E;padding:20px 24px;margin:0 0 24px;border-radius:4px">'
        '<p style="margin:0;color:#111827;font-size:15px;line-height:1.6"><strong style="color:#E7390E">What\'s next?</strong><br>'
        f'We\'ll review your request within 24 hours and send you an invitation link to <strong>{user_email}</strong> if approved.</p></div>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px">In the meantime, feel free to explore our '
        '<a href="https://docs.dakora.io" style="color:#E7390E;text-decoration:none;font-weight:600">documentation</a> to learn more about Dakora Studio.</p>'
        '<p style="margin:0;color:#4b5563;font-size:16px">Best regards,<br><strong>Dakora Team</strong></p>'
        '</td></tr>'
        '<tr><td style="background:#f9fafb;padding:30px 40px;text-align:center;border-top:1px solid #e5e7eb">'
        '<p style="margin:0 0 12px;color:#6b7280;font-size:14px">Questions? Contact us at '
        '<a href="mailto:support@dakora.io" style="color:#E7390E;text-decoration:none">support@dakora.io</a></p>'
        '<p style="margin:0;color:#9ca3af;font-size:12px">© 2025 Dakora Labs. All rights reserved.</p>'
        '</td></tr></table></td></tr></table></body></html>'
    )


def render_invitation_email(user_name: str, invite_url: str) -> str:
    """Render custom invitation email with Clerk invite link"""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Welcome to Dakora Studio</title></head>'
        '<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,\'Helvetica Neue\',Arial,sans-serif;background:#f9fafb">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 20px">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;box-shadow:0 4px 6px rgba(0,0,0,0.05);overflow:hidden">'
        '<tr><td style="background:#fff;padding:40px;text-align:center;border-bottom:1px solid #e5e7eb">'
        '<img src="https://playground.dakora.io/logo-light.png" alt="Dakora Studio" style="max-width:200px;height:auto;margin:0 auto;display:block">'
        '</td></tr>'
        '<tr><td style="padding:40px">'
        f'<p style="margin:0 0 24px;color:#4b5563;font-size:16px;line-height:1.6">Hi {user_name},</p>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px">Great news! Your request to join Dakora Studio has been approved. We\'re excited to have you on board!</p>'
        '<div style="background:#f0fdf4;border-left:4px solid #10b981;padding:20px 24px;margin:0 0 32px;border-radius:4px">'
        '<p style="margin:0;color:#111827;font-size:15px;line-height:1.6"><strong style="color:#10b981">Get Started:</strong><br>'
        'Click the button below to accept your invitation and create your account. This link will expire in 7 days.</p></div>'
        '<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:0 0 24px">'
        f'<a href="{invite_url}" style="display:inline-block;background:#E7390E;color:#fff;font-size:16px;font-weight:600;text-decoration:none;padding:14px 32px;border-radius:8px">Accept Invitation</a>'
        '</td></tr></table>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px">Need help getting started? Check out our '
        '<a href="https://docs.dakora.io" style="color:#E7390E;text-decoration:none;font-weight:600">documentation</a> for guides and tutorials.</p>'
        '<p style="margin:0;color:#4b5563;font-size:16px">Best regards,<br><strong>Dakora Team</strong></p>'
        '</td></tr>'
        '<tr><td style="background:#f9fafb;padding:30px 40px;text-align:center;border-top:1px solid #e5e7eb">'
        '<p style="margin:0 0 12px;color:#6b7280;font-size:14px">Questions? Contact us at '
        '<a href="mailto:support@dakora.io" style="color:#E7390E;text-decoration:none">support@dakora.io</a></p>'
        '<p style="margin:0;color:#9ca3af;font-size:12px">© 2025 Dakora Labs. All rights reserved.</p>'
        '</td></tr></table></td></tr></table></body></html>'
    )


def render_rejection_email(user_name: str) -> str:
    """Render polite rejection email for invitation request"""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Dakora Studio Invitation Update</title></head>'
        '<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,\'Helvetica Neue\',Arial,sans-serif;background:#f9fafb">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 20px">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;box-shadow:0 4px 6px rgba(0,0,0,0.05);overflow:hidden">'
        '<tr><td style="background:#fff;padding:40px;text-align:center;border-bottom:1px solid #e5e7eb">'
        '<img src="https://playground.dakora.io/logo-light.png" alt="Dakora Studio" style="max-width:200px;height:auto;margin:0 auto;display:block">'
        '</td></tr>'
        '<tr><td style="padding:40px">'
        f'<p style="margin:0 0 24px;color:#4b5563;font-size:16px;line-height:1.6">Hi {user_name},</p>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px">Thank you for your interest in Dakora Studio. We appreciate you taking the time to request access.</p>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px">After careful review, we\'ve decided not to approve your invitation request at this time. This decision is based on our current capacity and the specific use cases we\'re prioritizing during our invite-only phase.</p>'
        '<div style="background:#fefce8;border-left:4px solid #f59e0b;padding:20px 24px;margin:0 0 24px;border-radius:4px">'
        '<p style="margin:0;color:#111827;font-size:15px;line-height:1.6"><strong style="color:#f59e0b">We\'d Love to Stay Connected</strong><br>'
        'This isn\'t a permanent no! We\'re constantly expanding access and would be happy to reconsider your application in the future.</p></div>'
        '<p style="margin:0 0 24px;color:#4b5563;font-size:16px">You\'re welcome to submit another request when your use case evolves, or reach out to us directly at '
        '<a href="mailto:support@dakora.io" style="color:#E7390E;text-decoration:none;font-weight:600">support@dakora.io</a> to discuss your specific needs.</p>'
        '<p style="margin:0;color:#4b5563;font-size:16px">Thank you again for your interest!<br><br>Best regards,<br><strong>Dakora Team</strong></p>'
        '</td></tr>'
        '<tr><td style="background:#f9fafb;padding:30px 40px;text-align:center;border-top:1px solid #e5e7eb">'
        '<p style="margin:0 0 12px;color:#6b7280;font-size:14px">Questions? Contact us at '
        '<a href="mailto:support@dakora.io" style="color:#E7390E;text-decoration:none">support@dakora.io</a></p>'
        '<p style="margin:0;color:#9ca3af;font-size:12px">© 2025 Dakora Labs. All rights reserved.</p>'
        '</td></tr></table></td></tr></table></body></html>'
    )
