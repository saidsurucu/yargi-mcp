import os, stripe
from clerk_backend_api import Clerk                         # Clerk backend SDK
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET")
clerk         = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

@router.post("/stripe/webhook")
async def stripe_hook(req: Request):
    payload, sig = await req.body(), req.headers["stripe-signature"]
    try:
        event = stripe.Webhook.construct_event(             # Stripe-recommended verify
            payload, sig, os.getenv("STRIPE_WEBHOOK_SECRET"))
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Bad sig")

    if event["type"] == "customer.subscription.updated":
        item   = event["data"]["object"]["items"]["data"][0]
        plan   = item["price"]["nickname"]                  # "Pro", "Enterprise"…
        userID = event["data"]["object"]["metadata"]["clerk_user_id"]
        clerk.users.update_user_metadata(                   # merge into unsafe_metadata
            userID, unsafe_metadata={"plan": plan})
    return {"ok": True}
    
