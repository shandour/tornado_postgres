//the relevants buttons (e.traget and its counterpart) have to contain the id field which is the post's database id and a name which indicates its action type: like-btn or dislike-btn; button.value represents the attitude sent as a query string--like or dislike--respectively


function reactToPost(e, _xsrf_token) {
    var btn = e.target;
    console.log(btn)
    var attitude = btn.value;

    var req = new Request((`/posts/${btn.id}?attitude=${attitude}`),
                          {method: "PUT",
                           body: new URLSearchParams({"_xsrf": _xsrf_token}),
                           credentials: "same-origin"});

    fetch(req).then(res => {
        if (res.ok) {
            return res.json();
        } else {
            throw res.status;
        }
    }).then(jsn => {
        var likesNumElement = document.getElementById(`likes-number-${btn.id}`);
        var numLikes = Number(likesNumElement.textContent);
        likesNumElement.textContent = numLikes + jsn['likes'];

        var disLikesNumElement = document.getElementById(`dislikes-number-${btn.id}`);
        var numDisLikes = Number(disLikesNumElement.textContent);
        disLikesNumElement.textContent = numDisLikes + jsn['dislikes'];

        if (attitude == 'like') {
            var opposingBtn = document.querySelector(`button[id='${btn.id}'][name='dislike-btn']`)
            if (btn.className == "btn btn-dark likes-dislikes-btn") {
                btn.className = "btn btn-light likes-dislikes-btn";
            } else {
                btn.className = "btn btn-dark likes-dislikes-btn";
            }
            opposingBtn.className = "btn btn-light likes-dislikes-btn";
        } else {
            var opposingBtn = document.querySelector(`button[id='${btn.id}'][name='like-btn']`)
            if (btn.className == "btn btn-dark likes-dislikes-btn") {
                btn.className = "btn btn-light likes-dislikes-btn";
            } else {
                btn.className = "btn btn-dark likes-dislikes-btn";
            }
            opposingBtn.className = "btn btn-light likes-dislikes-btn";
        }
    });
}
